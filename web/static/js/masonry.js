// Shared responsive masonry layout for grids of images.
// Items are plain DOM elements with a `data-image-url` attribute used to
// determine their aspect ratio; the caller decides what happens on click.
function columnCountForWidth(width) {
	if (width < 500) return 1;
	if (width < 768) return 2;
	if (width < 992) return 3;
	if (width < 1400) return 4;
	return 5;
}

function getItemAspectRatios(items) {
	// Preload every image so we know its aspect ratio up front — this lets
	// us assign items to the shortest column synchronously, instead of
	// racing against async image loads.
	return Promise.all(
		items.map(
			(item) =>
				new Promise((resolve) => {
					var img = new Image();
					var finish = () => {
						resolve((img.naturalHeight || 1) / (img.naturalWidth || 1) || 1);
					};
					img.addEventListener("load", finish);
					img.addEventListener("error", finish);
					img.src = item.dataset.imageUrl;
				}),
		),
	);
}

function renderMasonry(containerEl, items, ratios, onItemClick) {
	var columnCount = columnCountForWidth(
		containerEl.clientWidth || containerEl.parentElement.clientWidth,
	);
	containerEl.innerHTML = "";

	var columns = [];
	var heights = [];
	var i, col;
	for (i = 0; i < columnCount; i++) {
		col = document.createElement("div");
		col.className = "gallery-masonry-col";
		containerEl.appendChild(col);
		columns.push(col);
		heights.push(0);
	}

	items.forEach((originalItem, index) => {
		var item = originalItem.cloneNode(true);
		if (onItemClick) {
			item.addEventListener("click", () => {
				onItemClick(index);
			});
		}

		// Place the item into the currently shortest column.
		var shortestIndex = heights.indexOf(Math.min.apply(null, heights));
		columns[shortestIndex].appendChild(item);
		heights[shortestIndex] += ratios[index];
	});
}

// Lays out `items` (an array of DOM elements with `data-image-url`) inside
// `containerEl` using a responsive masonry grid, re-laying out on resize.
// `onItemClick(index)` is called when an item is clicked, if provided.
// biome-ignore lint/correctness/noUnusedVariables: called from inline <script> in templates
function initMasonry(containerEl, items, onItemClick) {
	if (!containerEl || !items.length) return;

	var itemAspectRatios = null;

	function layout() {
		if (itemAspectRatios) {
			renderMasonry(containerEl, items, itemAspectRatios, onItemClick);
			return;
		}

		getItemAspectRatios(items).then((ratios) => {
			itemAspectRatios = ratios;
			renderMasonry(containerEl, items, ratios, onItemClick);
		});
	}

	layout();

	var resizeTimeout;
	window.addEventListener("resize", () => {
		clearTimeout(resizeTimeout);
		resizeTimeout = setTimeout(layout, 200);
	});
}
