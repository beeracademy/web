<script>
	export let game_data;
	export let ordered_gameplayers;

	import { userColors } from "./globals.js";

	let canvas;
	$: {
		const start_datetime = new Date(game_data.start_datetime);
		const end_datetime = game_data.end_datetime? new Date(game_data.end_datetime): undefined;

		const datasets = [{
			label: "Time",
			fill: false,
			lineTension: 0,
			backgroundColor: userColors[0],
			borderColor: userColors[0],
			data: [],
		}];

		for (let i = 0; i < game_data.cards.length; i++) {
			datasets[0].data.push(new Date(game_data.cards[i].drawn_datetime));
		}

		const labels = [];
		for (let i = 0; i < game_data.cards.length; i++) {
			labels.push(i);
		}

		const config = {
			type: "line",
			data: {
				labels: labels,
				datasets: datasets
			},
			options: {
				responsive: true,
				animation: false,
				legend: {
					display: false,
				},
				scales: {
					xAxes: [{
						scaleLabel: {
							display: true,
							labelString: "Turn",
						},
						ticks: {
							min: 0
						},
					}],
					yAxes: [{
						scaleLabel: {
							display: true,
							labelString: "Time",
						},
						ticks: {
							min: start_datetime,
							max: end_datetime,
							stepSize: 10 * 60 * 1000,
							callback: function (value) {
								const msDiff = value - start_datetime;
								return window.formatDuration(msDiff);
							},
						},
					}],
				},
				tooltips: {
					callbacks: {
						label: function(tooltipItem, data) {
							const index = tooltipItem.index;
							const player_name = ordered_gameplayers[index % game_data.playerCount].user.username;
							const previous = index === 0? start_datetime: data.datasets[0].data[index - 1];
							const msDiff = parseInt(tooltipItem.value) - previous;
							return player_name + "'s turn time: " + window.formatDuration(msDiff);
						},
					},
				},
			}
		};

		if (canvas) {
			const ctx = canvas.getContext("2d");
			new window.Chart(ctx, config);
		}
	}
</script>


<div>
{#if game_data.cards.length > 0 && game_data.cards[0].drawn_datetime === null}
	<p style="text-align: center;">Time graph unavailable due to missing data</p>
{:else}
	<canvas bind:this={canvas}></canvas>
{/if}
</div>
