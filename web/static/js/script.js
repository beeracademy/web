$("[data-href]").click(function(e) {
    var url = this.getAttribute("data-href");
    var openInNew = e.ctrlKey || (e.metaKey && navigator.userAgent.indexOf("Mac OS X"));

    if (openInNew) {
        window.open(url, "_blank");
    } else {
        window.location.href = url;
    }
});

function twoPad(s) {
    s = s.toString();
    if (s.split(".")[0].length == 1) {
        s = "0" + s;
    }
    return s;
}

function formatDuration(ms, seconds_decimals) {
    if (!seconds_decimals) {
        seconds_decimals = 0;
    }

    var round_constant = Math.pow(10, seconds_decimals);

    var total_seconds = Math.floor(ms / 1000 * round_constant) / round_constant;
    var seconds = (total_seconds % 60).toFixed(seconds_decimals);
    var total_minutes = Math.floor(total_seconds / 60);
    var minutes = total_minutes % 60;
    var total_hours = Math.floor(total_minutes / 60);

    return total_hours + ":" + twoPad(minutes) + ":" + twoPad(seconds);
}

function formatDate(d) {
    return moment(d).format("MMMM D, YYYY HH:mm:ss");
}

if ($(".live").length) {
    setInterval(function() {
        $(".live").each(function(i, el) {
            var start = new Date(parseFloat(el.getAttribute("data-start-time")) * 1000);
            var difference = Date.now() - start;
            var newDuration = formatDuration(difference);
            el.querySelector(".duration").textContent = newDuration;
        });
    }, 1000);
}
