export const card_constants = JSON.parse(
	document.getElementById("card_constants")?.textContent,
);
export const userColors = [
	"#006BA4",
	"#FF800E",
	"#ABABAB",
	"#595959",
	"#5F9ED1",
	"#C85200",
];

declare global {
	interface Window {
		is_authenticated: boolean;
		is_staff: boolean;
		formatDateWithoutTime: (d: Date) => string;
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
export const formatDateWithoutTime = window.formatDateWithoutTime;
export const formatDate = window.formatDate;
export const formatDuration = window.formatDuration;
export const toBase14 = window.toBase14;

export const moment = window.moment;
export const ApexCharts = window.ApexCharts;
export const L = window.L;
