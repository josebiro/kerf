export type BoardType = 'solid' | 'sheet' | 'thick_stock';
export type DisplayUnits = 'in' | 'mm';

export interface PartPreview {
	name: string;
	vertex_count: number;
}

export interface UploadResponse {
	session_id: string;
	file_url: string;
	parts_preview: PartPreview[];
}

export interface Part {
	name: string;
	quantity: number;
	length_mm: number;
	width_mm: number;
	thickness_mm: number;
	board_type: BoardType;
	stock: string;
	notes: string;
}

export interface ShoppingItem {
	material: string;
	thickness: string;
	quantity: number;
	unit: string;
	unit_price: number | null;
	subtotal: number | null;
	description: string;
	cut_pieces: string[];
	url: string | null;
}

export interface CostEstimate {
	items: ShoppingItem[];
	total: number | null;
	has_missing_prices: boolean;
}

export interface AnalyzeRequest {
	session_id: string;
	solid_species: string;
	sheet_type: string;
	all_solid?: boolean;
	display_units?: DisplayUnits;
}

export interface AnalyzeResponse {
	parts: Part[];
	shopping_list: ShoppingItem[];
	cost_estimate: CostEstimate;
	display_units: DisplayUnits;
}

export interface ProjectSummary {
	id: string;
	name: string;
	filename: string;
	solid_species: string;
	sheet_type: string;
	part_count: number;
	unique_parts: number;
	estimated_cost: number | null;
	thumbnail_url: string | null;
	created_at: string;
	updated_at: string;
}

export interface ProjectDetail {
	id: string;
	name: string;
	filename: string;
	solid_species: string;
	sheet_type: string;
	all_solid: boolean;
	display_units: DisplayUnits;
	analysis_result: AnalyzeResponse;
	file_url: string;
	thumbnail_url: string | null;
	created_at: string;
	updated_at: string;
}
