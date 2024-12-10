<script>
const { url } = $props();
</script>

<div class="center">
	<img src={url} alt="Uploaded game" />
</div>

<style>
	img {
		max-width: 100%;
	}
	.center {
		text-align: center;
	}
</style>
