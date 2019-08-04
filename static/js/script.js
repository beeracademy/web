$("tr[data-href]").click(function(e) {
    var url = this.getAttribute("data-href");
    var openInNew = e.ctrlKey || (e.metaKey && navigator.userAgent.indexOf("Mac OS X"));

    if (openInNew) {
        window.open(url, "_blank");
    } else {
        window.location.href = url;
    }
});
