<script>
	export let game_data;
	export let ordered_gameplayers;

	import { userColors } from "./globals.js";

	let canvas;
	$: {
		const datasets = [];
		for (let i = 0; i < game_data.playerCount; i++) {
			datasets.push({
				label: ordered_gameplayers[i].user.username,
				fill: false,
				lineTension: 0,
				backgroundColor: userColors[i],
				borderColor: userColors[i],
				data: [0],
			});
		}

		for (let i = 0; i < game_data.cards.length; i++) {
			const data = datasets[i % game_data.playerCount].data;
			data.push(data[data.length - 1] + game_data.cards[i].value);
		}

		const labels = [];
		for (let i = 0; i <= 13; i++) {
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
				scales: {
					xAxes: [{
						scaleLabel: {
							display: true,
							labelString: "Round",
						},
						ticks: {
							min: 0
						},
					}],
					yAxes: [{
						scaleLabel: {
							display: true,
							labelString: "Sips",
						},
						ticks: {
							min: 0
						},
					}],
				},
			}
		};

		if (canvas) {
			const ctx = canvas.getContext("2d");
			new window.Chart(ctx, config);
		}
	}
</script>

<canvas bind:this={canvas}></canvas>
