export const card_constants = JSON.parse(document.getElementById("card_constants")!.textContent!);
export const userColors = [
	"#16a085",
	"#27ae60",
	"#2980b9",
	"#8e44ad",
	"#2c3e50",
	"#f39c12",
	"#d35400",
	"#c0392b",
];

export declare const is_authenticated: boolean;
export declare const is_staff: boolean;
export declare const formatDate: (d: Date) => string;
export declare const formatDuration: (ms: number, second_decimals?: number) => string;

export declare const moment: any;
export declare const ApexCharts: any;
