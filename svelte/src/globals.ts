export const card_constants = JSON.parse(
	document.getElementById("card_constants")?.textContent,
);
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

declare global {
	interface Window {
		is_authenticated: boolean;
		is_staff: boolean;
		formatDate: (d: Date) => string;
		formatDuration: (ms: number, seconds_decimals?: number) => string;
		toBase14: (s: number) => string;
		// biome-ignore lint/suspicious/noExplicitAny: ...
		moment: any;
		// biome-ignore lint/suspicious/noExplicitAny: ...
		ApexCharts: any;
		// biome-ignore lint/suspicious/noExplicitAny: ...
		L: any;
	}
}

export const is_authenticated = window.is_authenticated;
export const is_staff = window.is_staff;
export const formatDate = window.formatDate;
export const formatDuration = window.formatDuration;
export const toBase14 = window.toBase14;

export const moment = window.moment;
export const ApexCharts = window.ApexCharts;
export const L = window.L;
