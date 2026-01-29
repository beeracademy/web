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

window.gamesHeatmap = function gamesHeatmap(el, data) {
	const options = {
		series: data.series,
		xaxis: {
			categories: data.categories,
		},
		grid: {
			position: "front",
			xaxis: {
				lines: {
					show: true,
				},
			},
			yaxis: {
				lines: {
					show: true,
				},
			},
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
		chart: {
			height: 200,
			type: "heatmap",
		},
		dataLabels: {
			enabled: false,
		},
		colors: ["#008FFB"],
	};

	const chart = new ApexCharts(el, options);
	chart.render();

	return chart;
};
