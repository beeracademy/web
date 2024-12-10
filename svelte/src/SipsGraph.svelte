<script lang="ts">
import type { GameData, GamePlayerData } from "./types";

import { onMount } from "svelte";
import { ApexCharts, toBase14, userColors } from "./globals";
interface Props {
	game_data: GameData;
	ordered_gameplayers: GamePlayerData[];
}

const { game_data, ordered_gameplayers }: Props = $props();

// biome-ignore lint/style/useConst: Svelte 5
let container: HTMLElement = $state();
// biome-ignore lint/suspicious/noExplicitAny: ...
let chart: any;

let lastLength = -1;

const yaxis = {
	title: {
		text: "Sips (base 14)",
	},
	min: 0,
	max: 14,
	tickAmount: 1,
	labels: {
		formatter: (value: number) => toBase14(value),
	},
};

function updateChart(game_data: GameData) {
	if (!chart) return;
	if (game_data.cards.length === lastLength) return;
	lastLength = game_data.cards.length;

	const series = [];
	for (let i = 0; i < ordered_gameplayers.length; i++) {
		series.push({
			name: ordered_gameplayers[i].user.username,
			data: [[0, 0]],
		});
	}

	for (let i = 0; i < game_data.cards.length; i++) {
		const data = series[i % ordered_gameplayers.length].data;
		data.push([
			data.length,
			data[data.length - 1][1] + game_data.cards[i].value,
		]);
	}

	chart.updateSeries(series);

	let max = 0;
	for (let i = 0; i < ordered_gameplayers.length; i++) {
		const data = series[i].data;
		max = Math.max(max, data[data.length - 1][1]);
	}

	const maxRounded = Math.ceil(max / 14) * 14;

	yaxis.max = maxRounded;
	yaxis.tickAmount = maxRounded / 14;

	chart.updateOptions({
		yaxis: yaxis,
	});
}

onMount(() => {
	const options = {
		chart: {
			type: "line",
			height: 500,
		},
		stroke: {
			curve: "straight",
		},
		xaxis: {
			type: "numeric",
			title: {
				text: "Round",
			},
			tickAmount: "dataPoints",
			labels: {
				formatter: (value: number) => Math.round(value),
			},
		},
		yaxis: yaxis,
		colors: userColors,
		series: [],
	};

	chart = new ApexCharts(container, options);
	chart.render();

	updateChart(game_data);
});

$effect(() => {
	updateChart(game_data);
});
</script>

<div bind:this={container}></div>
