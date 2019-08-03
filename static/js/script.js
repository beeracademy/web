$('tr[data-href]').click(function() {
    window.location.href = this.getAttribute('data-href');
});