/* ==========================================================================
   DV Maestro landing page — behaviour
   ========================================================================== */
(function () {
  'use strict';

  /* ------------------------------------------------------ nav dropdowns */
  var items = Array.prototype.slice.call(document.querySelectorAll('[data-dropdown]'));

  function closeAll(except) {
    items.forEach(function (item) {
      if (item === except) return;
      item.querySelector('.nav__trigger').setAttribute('aria-expanded', 'false');
      item.querySelector('.nav__panel').hidden = true;
    });
  }

  var hoverCapable = window.matchMedia('(hover: hover)').matches;

  items.forEach(function (item) {
    var trigger = item.querySelector('.nav__trigger');
    var panel   = item.querySelector('.nav__panel');

    function set(open) {
      trigger.setAttribute('aria-expanded', String(open));
      panel.hidden = !open;
    }

    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      // On hover devices the panel is already open by the time the click
      // lands, so only handle keyboard activation there (detail === 0).
      if (hoverCapable && e.detail !== 0) return;
      var open = trigger.getAttribute('aria-expanded') === 'true';
      closeAll(item);
      set(!open);
    });

    if (hoverCapable) {
      item.addEventListener('mouseenter', function () { closeAll(item); set(true); });
      item.addEventListener('mouseleave', function () { set(false); });
      item.addEventListener('focusout', function (e) {
        if (!item.contains(e.relatedTarget)) set(false);
      });
    }
  });

  document.addEventListener('click', function () { closeAll(null); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeAll(null);
  });

  /* --------------------------------------------------------- mobile nav */
  var burger = document.querySelector('.nav__burger');
  var mobile = document.getElementById('mobile-menu');

  if (burger && mobile) {
    burger.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = burger.getAttribute('aria-expanded') === 'true';
      burger.setAttribute('aria-expanded', String(!open));
      burger.setAttribute('aria-label', open ? 'Open menu' : 'Close menu');
      mobile.hidden = open;
    });

    mobile.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        burger.setAttribute('aria-expanded', 'false');
        mobile.hidden = true;
      }
    });
  }

  /* -------------------------------------------------- revenue calculator */
  var calculator = document.getElementById('calculator');
  if (!calculator) return;

  var inputs = {
    units:    calculator.querySelector('[data-input="units"]'),
    adoption: calculator.querySelector('[data-input="adoption"]'),
    price:    calculator.querySelector('[data-input="price"]')
  };

  function out(name) { return calculator.querySelector('[data-out="' + name + '"]'); }

  var money = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  });

  function paint(input) {
    var min = Number(input.min), max = Number(input.max), val = Number(input.value);
    input.style.setProperty('--pct', ((val - min) / (max - min)) * 100 + '%');
  }

  function render() {
    var units    = Number(inputs.units.value);
    var adoption = Number(inputs.adoption.value);
    var price    = Number(inputs.price.value);

    var monthly = units * (adoption / 100) * price;
    var annual  = monthly * 12;

    out('units').textContent    = String(units);
    out('adoption').textContent = adoption + '%';
    out('price').textContent    = '$' + price;

    out('annualBig').textContent = money.format(annual);
    out('annual').textContent    = money.format(annual);
    out('monthly').textContent   = money.format(monthly);
    out('quarterly').textContent = money.format(monthly * 3);

    out('formula').textContent =
      units + ' units × ' + adoption + '% adoption × $' + price + '/mo × 12';

    Object.keys(inputs).forEach(function (k) { paint(inputs[k]); });
  }

  Object.keys(inputs).forEach(function (k) {
    inputs[k].addEventListener('input', render);
  });

  render();
})();
