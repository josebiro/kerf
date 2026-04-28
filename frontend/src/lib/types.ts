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
