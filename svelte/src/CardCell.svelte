<svelte:options immutable />

<script context="module" lang="ts">
  import { card_constants } from "./globals";
</script>

<script lang="ts">
  export let card: any;

  import ColoredSuit from "./ColoredSuit.svelte";

  let valueName = "",
    suitName = "";

  if (card) {
    valueName = card_constants.value_names[card.value];
    suitName = card_constants.suit_names[card.suit];
  }
</script>

{#if card}
  <td title="{valueName} of {suitName}">
    <span class="symbol">
      <ColoredSuit {card} />
    </span>
    {card.value}
  </td>
{:else}
  <td />
{/if}

<style>
  .symbol {
    width: 1rem;
    display: inline-block;
  }
</style>
