#!/usr/bin/env python3
"""Run all registered supplier crawlers and upsert results to Supabase.

Usage:
    python run_crawl.py                    # Crawl all active suppliers
    python run_crawl.py woodworkers_source # Crawl specific supplier
    python run_crawl.py --list             # List registered crawlers
"""

import sys
import logging
from datetime import datetime, timezone

from app.supabase_client import get_supabase_client
from app.suppliers.crawler_base import CrawlerBase
from app.suppliers.woodworkers_source import WoodworkersSourceCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CRAWLERS: dict[str, type[CrawlerBase]] = {
    "woodworkers_source": WoodworkersSourceCrawler,
}


def run_crawler(crawler_cls: type[CrawlerBase]) -> None:
    """Run a single crawler and upsert results to Supabase."""
    crawler = crawler_cls()
    client = get_supabase_client()
    started_at = datetime.now(timezone.utc)

    logger.info("Starting crawl: %s (%s)", crawler.supplier_name, crawler.supplier_id)

    errors: list[str] = []
    try:
        products = crawler.crawl()
    except Exception as e:
        errors.append(str(e))
        products = []
        logger.error("Crawl failed for %s: %s", crawler.supplier_id, e)

    upserted = 0
    for product in products:
        try:
            client.table("supplier_prices").upsert(
                {
                    "supplier_id": product.supplier_id,
                    "product_type": product.product_type,
                    "species_or_name": product.species_or_name,
                    "thickness": product.thickness,
                    "price": float(product.price),
                    "unit": product.unit,
                    "url": product.url,
                    "crawled_at": product.crawled_at.isoformat(),
                },
                on_conflict="supplier_id,product_type,species_or_name,thickness",
            ).execute()
            upserted += 1
        except Exception as e:
            errors.append(f"Upsert failed for {product.species_or_name}: {e}")

    finished_at = datetime.now(timezone.utc)
    client.table("crawl_runs").insert({
        "supplier_id": crawler.supplier_id,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "product_count": upserted,
        "errors": errors if errors else None,
    }).execute()

    logger.info(
        "Finished %s: %d products upserted, %d errors, %.1fs",
        crawler.supplier_id, upserted, len(errors),
        (finished_at - started_at).total_seconds(),
    )


def main():
    if "--list" in sys.argv:
        print("Registered crawlers:")
        for sid, cls in CRAWLERS.items():
            print(f"  {sid}: {cls.supplier_name} ({cls.base_url})")
        return

    targets = [a for a in sys.argv[1:] if not a.startswith("-")]
    if targets:
        for sid in targets:
            if sid not in CRAWLERS:
                logger.error("Unknown supplier: %s", sid)
                continue
            run_crawler(CRAWLERS[sid])
    else:
        for crawler_cls in CRAWLERS.values():
            run_crawler(crawler_cls)


if __name__ == "__main__":
    main()
