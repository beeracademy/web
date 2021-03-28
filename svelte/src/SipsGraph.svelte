<script lang="ts">
  import type { GameData, GamePlayerData } from "./types";

  export let game_data: GameData;
  export let ordered_gameplayers: GamePlayerData[];

  import { onMount } from "svelte";
  import { userColors, ApexCharts } from "./globals.js";

  let container: HTMLElement;
  let chart: any;

  let lastLength = -1;

  const yaxis = {
    title: {
      text: "Sips (base 14)"
    },
    min: 0,
    labels: {
      formatter: function(val, index) {
        return window.toBase14(val);
      }
    },
  };

  function updateChart() {
    if (!chart) return;
    if (game_data.cards.length === lastLength) return;
    lastLength = game_data.cards.length;

    const series = [];
    for (let i = 0; i < game_data.playerCount; i++) {
      series.push({
        name: ordered_gameplayers[i].user.username,
        data: [[0, 0]]
      });
    }

    for (let i = 0; i < game_data.cards.length; i++) {
      const data = series[i % game_data.playerCount].data;
      data.push([
        data.length,
        data[data.length - 1][1] + game_data.cards[i].value
      ]);
    }

    chart.updateSeries(series);

    let max = 0;
    for (let i = 0; i < game_data.playerCount; i++) {
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
        height: 500
      },
      stroke: {
        curve: "straight"
      },
      xaxis: {
        type: "numeric",
        title: {
          text: "Round"
        },
        tickAmount: "dataPoints",
        labels: {
          formatter: function(value: number, _timestamp: any, _index: any) {
            return Math.round(value);
          }
        }
      },
      yaxis: yaxis,
      colors: userColors,
      series: []
    };

    chart = new ApexCharts(container, options);
    chart.render();

    updateChart();
  });

  $: if (game_data) {
    updateChart();
  }
</script>

<div bind:this={container} />
