$("tr[data-href]").click(function(e) {
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
    if (s.length == 1) {
        s = "0" + s;
    }
    return s;
}

function formatDuration(ms) {
    var total_seconds = Math.floor(ms / 1000);
    var seconds = total_seconds % 60;
    var total_minutes = Math.floor(total_seconds / 60);
    var minutes = total_minutes % 60;
    var total_hours = Math.floor(total_minutes / 60);

    return total_hours + ":" + twoPad(minutes) + ":" + twoPad(seconds);
}
