<script module lang="ts">
import { card_constants } from "./globals";
import type { CardData } from "./types";
</script>

<script lang="ts">
	interface Props {
		card: CardData;
	}

	let { card }: Props = $props();

	const [symbol, color] = card_constants.suit_symbols[card.suit];
</script>

<span style="color: {color};">{symbol}</span>
