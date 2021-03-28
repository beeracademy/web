<script context="module" lang="ts">
  import type { ChugData } from "./types";
  import { formatDuration } from "./globals";
</script>

<script lang="ts">
  export let start_datetime: string;
  export let chug: ChugData;
  export let dnf: boolean;

  import ColoredSuit from "./ColoredSuit.svelte";

  const player = chug.player!;
  $: card = chug.card;

  let intervalId: number | null = null;
  let durationStr = "";

  function start_delta_ms() {
    return Date.now() - new Date(start_datetime).getTime();
  }

  function updateDuration() {
    durationStr = formatDuration(
      start_delta_ms() - card.chug_start_start_delta_ms!,
      3
    );
  }

  $: {
    if (intervalId !== null) {
      clearInterval(intervalId);
    }

    if (dnf) {
      durationStr = "DNF";
    } else if (card.chug_duration_ms) {
      durationStr = formatDuration(card.chug_duration_ms, 3);
    } else if (card.chug_start_start_delta_ms) {
      if (dnf) {
        durationStr = "DNF";
      } else {
        intervalId = setInterval(updateDuration, 10);
      }
    } else {
      durationStr = "Not started";
    }
  }
</script>

<div class="col-md-auto">
  <div class="card">
    <div class="card-header">
      <ColoredSuit {card} />
    </div>
    <ul class="list-group list-group-flush">
      <li class="list-group-item">
        <a href="/players/{player.id}/">
          {player.username}
        </a>
      </li>
      <li class="list-group-item">
        {durationStr}
      </li>
      {#if card.chug_id}
        <li class="list-group-item staff-only">
          <a
            class="btn btn-primary text-light"
            href="/admin/games/chug/{card.chug_id}"
            style="width: 100%;">Edit</a
          >
        </li>
      {/if}
    </ul>
  </div>
</div>

<style>
  .card-header {
    font-size: 4rem;
    text-align: center;
  }
</style>
