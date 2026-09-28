// CyveTech UI — the sign-in page (www/login.html). Loaded right after the
// page's markup, so everything it touches is already there.

(function () {
	var page = document.getElementById("cvt-login");
	if (!page) return;

	// Frappe's login.js shows one step at a time, chosen by the address's
	// #hash. The heading at the top of the card belongs to signing in; the
	// other steps (forgot password, sign up...) keep the heading Frappe gives
	// them. The stylesheet reads the step from data-step.
	function step() {
		var hash = window.location.hash.slice(1).replace(/[^a-z-]/gi, "");
		page.setAttribute("data-step", hash || "login");
	}
	step();
	window.addEventListener("hashchange", step);

	// The background photo only if it can fill the window sharply. A small
	// picture stretched to that size looks blurry, and the brand backdrop
	// stays instead. (The address was checked on the server: login_rules.py.)
	var MIN_PHOTO_WIDTH = 1600;
	var photo = page.getAttribute("data-photo");
	if (photo) {
		var picture = new Image();
		picture.onload = function () {
			if (picture.naturalWidth >= MIN_PHOTO_WIDTH) {
				page.style.setProperty("--cvt-login-photo", 'url("' + photo + '")');
				page.classList.add("cvt-login-has-photo");
			}
		};
		picture.src = photo;
	}
})();
