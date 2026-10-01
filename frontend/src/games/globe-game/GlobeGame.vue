<script setup lang="ts">
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { onMounted, onUnmounted, ref } from "vue";

const containerRef = ref<HTMLDivElement | null>(null);
const score = ref(0);
const timeLeft = ref(30);
const gameOver = ref(false);

let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let globe: THREE.Mesh;
let targets: THREE.Group;
let animationId: number;
let controls: OrbitControls;
const timerInterval = ref<ReturnType<typeof setInterval> | null>(null);
let mouseDownPos = { x: 0, y: 0 };

const initThree = () => {
	if (!containerRef.value) return;

	const width = containerRef.value.clientWidth;
	const height = 500;

	scene = new THREE.Scene();
	camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
	camera.position.z = 12;

	renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
	renderer.setSize(width, height);
	renderer.setPixelRatio(window.devicePixelRatio);
	containerRef.value.appendChild(renderer.domElement);

	controls = new OrbitControls(camera, renderer.domElement);
	controls.enableDamping = true;
	controls.dampingFactor = 0.05;
	controls.minDistance = 6;
	controls.maxDistance = 20;

	const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
	scene.add(ambientLight);
	const sunLight = new THREE.DirectionalLight(0xffffff, 1);
	sunLight.position.set(5, 3, 5);
	scene.add(sunLight);

	const textureLoader = new THREE.TextureLoader();
	const earthTexture = textureLoader.load(
		"https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg",
	);
	const earthBumpMap = textureLoader.load(
		"https://unpkg.com/three-globe/example/img/earth-topology.png",
	);

	const geometry = new THREE.SphereGeometry(5, 64, 64);
	const material = new THREE.MeshPhongMaterial({
		map: earthTexture,
		bumpMap: earthBumpMap,
		bumpScale: 0.05,
		specular: new THREE.Color("grey"),
		shininess: 5,
	});
	globe = new THREE.Mesh(geometry, material);
	scene.add(globe);

	const starGeometry = new THREE.BufferGeometry();
	const starMaterial = new THREE.PointsMaterial({ color: 0xffffff });
	const starVertices = [];
	for (let i = 0; i < 10000; i++) {
		const x = (Math.random() - 0.5) * 2000;
		const y = (Math.random() - 0.5) * 2000;
		const z = (Math.random() - 0.5) * 2000;
		starVertices.push(x, y, z);
	}
	starGeometry.setAttribute(
		"position",
		new THREE.Float32BufferAttribute(starVertices, 3),
	);
	const stars = new THREE.Points(starGeometry, starMaterial);
	scene.add(stars);

	targets = new THREE.Group();
	scene.add(targets);

	spawnTarget();

	const animate = () => {
		animationId = requestAnimationFrame(animate);
		controls.update();
		renderer.render(scene, camera);
	};
	animate();

	window.addEventListener("resize", onWindowResize);
};

const onWindowResize = () => {
	if (!containerRef.value || !camera || !renderer) return;
	const width = containerRef.value.clientWidth;
	camera.aspect = width / 500;
	camera.updateProjectionMatrix();
	renderer.setSize(width, 500);
};

const spawnTarget = () => {
	targets.clear();

	const phi = Math.random() * Math.PI * 2;
	const theta = Math.random() * Math.PI;
	const radius = 5.05;

	const x = radius * Math.sin(theta) * Math.cos(phi);
	const y = radius * Math.cos(theta);
	const z = radius * Math.sin(theta) * Math.sin(phi);

	const targetGeo = new THREE.SphereGeometry(0.15, 16, 16);
	const targetMat = new THREE.MeshBasicMaterial({
		color: 0xff0000,
		transparent: true,
		opacity: 0.8,
	});
	const target = new THREE.Mesh(targetGeo, targetMat);

	const ringGeo = new THREE.RingGeometry(0.2, 0.25, 32);
	const ringMat = new THREE.MeshBasicMaterial({
		color: 0xff0000,
		side: THREE.DoubleSide,
	});
	const ring = new THREE.Mesh(ringGeo, ringMat);
	ring.lookAt(new THREE.Vector3(0, 0, 0));
	target.add(ring);

	target.position.set(x, y, z);
	target.lookAt(x * 2, y * 2, z * 2);

	targets.add(target);
};

const handleMouseDown = (event: MouseEvent) => {
	mouseDownPos = { x: event.clientX, y: event.clientY };
};

const handleCanvasClick = (event: MouseEvent) => {
	if (gameOver.value) return;

	const dist = Math.hypot(
		event.clientX - mouseDownPos.x,
		event.clientY - mouseDownPos.y,
	);
	if (dist > 5) return;

	const rect = renderer.domElement.getBoundingClientRect();
	const mouse = new THREE.Vector2(
		((event.clientX - rect.left) / rect.width) * 2 - 1,
		-((event.clientY - rect.top) / rect.height) * 2 + 1,
	);

	const raycaster = new THREE.Raycaster();
	raycaster.setFromCamera(mouse, camera);

	const intersects = raycaster.intersectObjects(targets.children, true);

	if (intersects.length > 0) {
		score.value += 1;
		spawnTarget();
	}
};

const startTimer = () => {
	timeLeft.value = 30;
	if (timerInterval.value) clearInterval(timerInterval.value);
	timerInterval.value = setInterval(() => {
		if (timeLeft.value > 0) {
			timeLeft.value--;
		} else {
			gameOver.value = true;
			if (timerInterval.value) clearInterval(timerInterval.value);
			timerInterval.value = null;
		}
	}, 1000);
};

onMounted(() => {
	initThree();
	startTimer();
});

onUnmounted(() => {
	cancelAnimationFrame(animationId);
	window.removeEventListener("resize", onWindowResize);
	if (timerInterval.value) clearInterval(timerInterval.value);
	controls?.dispose();
	if (renderer) {
		renderer.dispose();
		renderer.domElement.remove();
	}
});

const restart = () => {
	score.value = 0;
	gameOver.value = false;
	spawnTarget();
	startTimer();
};
</script>

<template>
  <div class="flex flex-col items-center rounded-xl bg-[#0a0a1a] p-5 font-sans text-white">
    <div class="mb-5 flex gap-10 text-2xl font-bold">
      <div class="rounded-lg border border-white/20 bg-white/10 px-5 py-2.5">
        Pins Found: {{ score }}
      </div>
      <div class="rounded-lg border border-white/20 bg-white/10 px-5 py-2.5">
        Time: {{ timeLeft }}s
      </div>
    </div>

    <div
      ref="containerRef"
      class="relative h-[500px] w-full max-w-4xl cursor-crosshair overflow-hidden rounded-lg bg-[radial-gradient(circle_at_center,#1a1a3a_0%,#050510_100%)]"
      @mousedown.prevent="handleMouseDown"
      @click="handleCanvasClick"
    >
      <div
        v-if="gameOver"
        class="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/85"
      >
        <h2 class="m-0 text-5xl text-yellow-400">MISSION COMPLETE</h2>
        <p class="mb-5 mt-4 text-xl">You located {{ score }} targets on Earth!</p>
        <button
          @click="restart"
          class="cursor-pointer rounded border-none bg-emerald-600 px-6 py-3 text-lg font-bold text-white hover:bg-emerald-500"
        >
          Launch New Mission
        </button>
      </div>
    </div>

    <div class="mt-5 text-neutral-400">
      <b class="text-yellow-400">Drag</b> to rotate Earth, <b class="text-yellow-400">Scroll</b> to
      zoom. Find and click the <b class="text-yellow-400">Red Beacons</b>!
    </div>
  </div>
</template>
