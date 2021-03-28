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

const _window = window as any;

export const is_authenticated = _window.is_authenticated as boolean;
export const is_staff = _window.is_staff as boolean;
export const formatDate = _window.formatDate as (d: Date) => string;
export const formatDuration = _window.formatDuration as (ms: number, second_decimals?: number) => string;

export const moment = _window.moment;
export const ApexCharts = _window.ApexCharts;
