// Submit the filter form as soon as a sort or brand select changes.
document.querySelectorAll('[data-autosubmit]').forEach(function (el) {
  el.addEventListener('change', function () {
    el.form.submit();
  });
});
