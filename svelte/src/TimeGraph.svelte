<script>
  export let game_data;
  export let ordered_gameplayers;

  import { onMount } from "svelte";
  import { userColors } from "./globals.js";

  let container;
  let chart;

  let lastLength = -1;

  function updateChart() {
    if (!chart) return;
    if (game_data.cards.length === lastLength) return;
    lastLength = game_data.cards.length;

    const series = [
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

    window.series = series;
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
          formatter: function(value, timestamp, index) {
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
          formatter: function(val, index) {
            return window.formatDuration(val);
          }
        }
      },
      markers: {
        size: 1
      },
      tooltip: {
        x: {
          formatter: function(value, index) {
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
          formatter: function(val, { series, seriesIndex, dataPointIndex, w }) {
            const previous =
              dataPointIndex === 0
                ? 0
                : series[0][dataPointIndex - 1];
            const msDiff = val - previous;
            return "Turn time " + window.formatDuration(msDiff);
          }
        }
      },
      series: []
    };

    chart = new window.ApexCharts(container, options);
    chart.render();

    updateChart();
  });

  $: game_data, updateChart();
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
