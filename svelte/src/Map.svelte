<script lang="ts">
import { onMount } from "svelte";
import { L } from "./globals";
import type { Location } from "./types";

interface Props {
	location: Location;
}

const { location }: Props = $props();

// biome-ignore lint/style/useConst: Svelte 5
let mapEl: HTMLElement = $state();
onMount(() => {
	const map = L.map(mapEl).setView([location.latitude, location.longitude], 13);
	L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
		attribution:
			'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
	}).addTo(map);
	L.marker([location.latitude, location.longitude])
		.addTo(map)
		.bindPopup(`${location.latitude}, ${location.longitude}`);
	const circle = L.circle([location.latitude, location.longitude], {
		color: "red",
		fillColor: "#f03",
		fillOpacity: 0.5,
		radius: location.accuracy,
	}).addTo(map);
	map.fitBounds(map.getBounds().extend(circle.getBounds()));
});
</script>

<div class="map" bind:this={mapEl}></div>

<style>
	.map {
		height: 300px;
	}
</style>
