<svelte:options immutable />

<script context="module" lang="ts">
  import { card_constants } from "./globals";
  import type { CardData } from "./types";
</script>

<script lang="ts">
  export let card: CardData;

  const [symbol, color] = card_constants.suit_symbols[card.suit];
</script>

<span style="color: {color};">{symbol}</span>
