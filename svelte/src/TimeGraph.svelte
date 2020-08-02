<script lang="ts">
  import type { GameData, GamePlayerData } from "./types";

  export let game_data: GameData;
  export let ordered_gameplayers: GamePlayerData[];

  import { onMount } from "svelte";
  import { formatDuration, ApexCharts } from "./globals.js";

  let container: HTMLElement;
  let chart: any;

  let lastLength = -1;

  function updateChart() {
    if (!chart) return;
    if (game_data.cards.length === lastLength) return;
    lastLength = game_data.cards.length;

    const series: { name: string, data: number[] }[] = [
      {
        name: "Time",
        data: []
      }
    ];

    for (let i = 0; i < game_data.cards.length; i++) {
      series[0].data.push(
        game_data.cards[i].start_delta_ms
      );
    }

    chart.updateSeries(series);
  }

  onMount(() => {
    if (!container) return;

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
          text: "Turn"
        },
        tickAmount: "dataPoints",
        labels: {
          formatter: function(value: number, _timestamp: any, _index: any) {
            return Math.round(value);
          }
        }
      },
      yaxis: {
        type: "datetime",
        title: {
          text: "Time"
        },
        min: 0,
        labels: {
          formatter: function(val: number, _index: any) {
            return formatDuration(val);
          }
        }
      },
      markers: {
        size: 1
      },
      tooltip: {
        x: {
          formatter: function(value: number, _index: any) {
            const player_name =
              ordered_gameplayers[(value - 1) % game_data.playerCount].user
                .username;
            return (
              player_name +
              "'s turn " +
              Math.floor((value - 1) / game_data.playerCount + 1)
            );
          }
        },
        y: {
          formatter: function(val: number, { series, dataPointIndex } : { series: any, dataPointIndex: number }) {
            const previous =
              dataPointIndex === 0
                ? 0
                : series[0][dataPointIndex - 1];
            const msDiff = val - previous;
            return "Turn time " + formatDuration(msDiff);
          }
        }
      },
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

<div>
  {#if game_data.cards.length > 0 && game_data.cards[0].start_delta_ms === null}
    <p style="text-align: center;">
      Time graph unavailable due to missing data
    </p>
  {:else}
    <div bind:this={container} />
  {/if}
</div>
