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
	optimize_result: OptimizeResponse | null;
	file_url: string;
	thumbnail_url: string | null;
	created_at: string;
	updated_at: string;
}

export interface BufferConfig {
	sheet_mode: 'percentage' | 'extra_parts';
	sheet_value: number;
	lumber_mode: 'percentage' | 'extra_parts';
	lumber_value: number;
}

export interface BoardSizeConfig {
	width: number;
	length: number;
}

export interface Placement {
	part_name: string;
	x: number;
	y: number;
	width: number;
	height: number;
	rotated: boolean;
	is_spare: boolean;
}

export interface SheetLayout {
	material: string;
	width: number;
	length: number;
	placements: Placement[];
	waste_percent: number;
}

export interface BoardLayout {
	material: string;
	thickness: string;
	width: number;
	length: number;
	placements: Placement[];
	waste_percent: number;
}

export interface OptimizeSummary {
	total_sheets: number;
	total_boards: number;
	avg_waste_percent: number;
	total_spare_parts: number;
}

export interface SheetSizeConfig {
	width: number;
	length: number;
	label: string;
}

export interface OptimizeRequest {
	parts: Part[];
	shopping_list: ShoppingItem[];
	solid_species: string;
	sheet_type: string;
	buffer_config?: BufferConfig;
	board_sizes?: Record<string, BoardSizeConfig>;
	sheet_size?: SheetSizeConfig;
}

export interface OptimizeResponse {
	sheets: SheetLayout[];
	boards: BoardLayout[];
	summary: OptimizeSummary;
	updated_shopping_list: ShoppingItem[];
	buffer_config: BufferConfig;
	board_sizes: Record<string, BoardSizeConfig>;
	sheet_size: SheetSizeConfig;
}
