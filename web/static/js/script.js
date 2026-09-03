$('[data-toggle="tooltip"]').tooltip();

$("[data-href]").click(function (e) {
	if (e.target.nodeName === "A") return;
	const url = this.getAttribute("data-href");
	const openInNew =
		e.ctrlKey || (e.metaKey && navigator.userAgent.indexOf("Mac OS X"));

	if (openInNew) {
		window.open(url, "_blank");
	} else {
		window.location.href = url;
	}
});

function twoPad(v) {
	let s = v.toString();
	if (s.split(".")[0].length === 1) {
		s = `0${s}`;
	}
	return s;
}

function formatDuration(ms, seconds_decimals_input) {
	const seconds_decimals = seconds_decimals_input ?? 0;

	const round_constant = 10 ** seconds_decimals;

	const total_seconds =
		Math.floor((ms / 1000) * round_constant) / round_constant;
	const seconds = (total_seconds % 60).toFixed(seconds_decimals);
	const total_minutes = Math.floor(total_seconds / 60);
	const minutes = total_minutes % 60;
	const total_hours = Math.floor(total_minutes / 60);

	return `${total_hours}:${twoPad(minutes)}:${twoPad(seconds)}`;
}

window.formatDateWithoutTime = function formatDateWithoutTime(d) {
	return moment(d).format("MMM D, YYYY");
};

window.formatDate = function formatDate(d) {
	return moment(d).format("MMMM D, YYYY HH:mm:ss");
};

window.toBase14 = function toBase14(n) {
	return n.toString(14).toUpperCase();
};

if ($(".live").length) {
	setInterval(() => {
		$(".live").each((_i, el) => {
			const start = new Date(
				Number.parseFloat(el.getAttribute("data-start-time")) * 1000,
			);
			const difference = Date.now() - start;
			const newDuration = formatDuration(difference);
			el.querySelector(".duration").textContent = newDuration;
		});
	}, 1000);
}

$(".chooser-dropdown-searchable").on("shown.bs.dropdown", function () {
	const $input = $(this).find(".chooser-search-input");
	const input = $input.get(0);
	$input.val("");
	$(this).find(".chooser-option").show();
	if (input) {
		let attempts = 0;
		const focusInput = () => {
			input.focus({ preventScroll: true });
			input.select();
			attempts += 1;
			if (document.activeElement !== input && attempts < 8) {
				window.setTimeout(focusInput, 25);
			}
		};
		window.setTimeout(focusInput, 20);
	}
});

$(".chooser-dropdown-searchable > .dropdown-toggle").on("click", function () {
	const $dropdown = $(this).closest(".chooser-dropdown-searchable");
	window.setTimeout(() => {
		const input = $dropdown.find(".chooser-search-input").get(0);
		if (input) {
			input.focus({ preventScroll: true });
			input.select();
		}
	}, 60);
});

$(".chooser-dropdown-searchable .chooser-search-input").on(
	"input",
	function () {
		const query = this.value.trim().toLowerCase();
		const $dropdown = $(this).closest(".chooser-dropdown-searchable");
		$dropdown.find(".chooser-option").each((_i, option) => {
			const label = option.getAttribute("data-label") || "";
			option.style.display = label.includes(query) ? "" : "none";
		});
	},
);

$(".chooser-dropdown-menu .chooser-search-wrap").on("click", (e) => {
	e.stopPropagation();
});

window.gamesHeatmap = function gamesHeatmap(el, data, config) {
	const theme = config || {};
	const baseColor = theme.color || "#a5383b";
	const foreColor = theme.foreColor || "#aaa39b";
	const cellBg = theme.cellBackground || "rgba(255, 255, 255, 0.06)";
	const gapColor = theme.gapColor || "#343436";

	// Build a gradient color scale from the base color: an empty-day shade,
	// then four progressively more saturated steps of the base color so the
	// map reads as a smooth intensity gradient (GitHub contribution style)
	// instead of a couple of abrupt, blocky color jumps.
	const hexToRgb = (hex) => {
		const clean = hex.replace("#", "");
		const bigint = Number.parseInt(clean, 16);
		return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
	};
	const [r, g, b] = hexToRgb(baseColor);
	const shade = (alpha) => `rgba(${r}, ${g}, ${b}, ${alpha})`;

	const options = {
		series: data.series,
		chart: {
			height: theme.height || 200,
			type: "heatmap",
			background: "transparent",
			fontFamily: "inherit",
			foreColor,
			toolbar: { show: false },
			animations: { enabled: false },
		},
		theme: { mode: "dark" },
		xaxis: {
			categories: data.categories,
			axisBorder: { show: false },
			axisTicks: { show: false },
			labels: {
				style: {
					colors: foreColor,
					fontSize: "12px",
				},
			},
		},
		yaxis: {
			labels: {
				offsetX: -6,
				style: {
					colors: foreColor,
					fontSize: "12px",
				},
			},
		},
		grid: {
			show: false,
			padding: { left: 10, right: 0 },
		},
		plotOptions: {
			heatmap: {
				enableShades: false,
				distributed: false,
				radius: 4,
				colorScale: {
					ranges: [
						{ from: 0, to: 0, color: cellBg },
						{ from: 1, to: 1, color: shade(0.4) },
						{ from: 2, to: 2, color: shade(0.6) },
						{ from: 3, to: 3, color: shade(0.8) },
						{ from: 4, to: 999999, color: shade(1) },
					],
				},
			},
		},
		legend: {
			show: false,
		},
		stroke: {
			show: true,
			width: 4,
			colors: [gapColor],
		},
		tooltip: {
			y: {
				formatter: (value, _args) => {
					if (value === null) return "Out of season";
					const games = value === 1 ? "game" : "games";
					return `${value} ${games} played`;
				},
				title: {
					formatter: (_value, args) =>
						data.dates[args.seriesIndex][args.dataPointIndex],
				},
			},
		},
		dataLabels: {
			enabled: false,
		},
		colors: [baseColor],
	};

	const chart = new ApexCharts(el, options);
	chart.render();

	return chart;
};
