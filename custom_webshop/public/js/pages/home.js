(function () {
	"use strict";

	function initHeroCanvas() {
		const canvas = document.getElementById("toolpath-canvas");
		if (!canvas) return;
		const ctx = canvas.getContext("2d");
		let t = 0;
		function resize() {
			canvas.width = canvas.offsetWidth;
			canvas.height = canvas.offsetHeight;
		}
		function draw() {
			if (!ctx) return;
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			ctx.strokeStyle = "rgba(59, 130, 246, 0.35)";
			ctx.lineWidth = 1;
			ctx.beginPath();
			for (let x = 0; x < canvas.width; x += 8) {
				const y = canvas.height / 2 + Math.sin((x + t) * 0.02) * 40;
				x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
			}
			ctx.stroke();
			t += 2;
			requestAnimationFrame(draw);
		}
		resize();
		window.addEventListener("resize", resize);
		draw();
	}

	document.addEventListener("DOMContentLoaded", initHeroCanvas);
})();
