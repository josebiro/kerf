<script lang="ts" module>
	export type ModelViewerApi = {
		captureScreenshot: () => string | null;
	};
</script>

<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { get } from 'svelte/store';
	import * as THREE from 'three';
	import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
	import { ThreeMFLoader } from 'three/addons/loaders/3MFLoader.js';
	import { session } from '$lib/stores/auth';

	interface Props {
		fileUrl: string;
		api?: ModelViewerApi;
	}

	let { fileUrl, api = $bindable() }: Props = $props();
	let container: HTMLDivElement;
	let renderer: THREE.WebGLRenderer;
	let scene: THREE.Scene;
	let camera: THREE.PerspectiveCamera;
	let controls: OrbitControls;
	let animationId: number;

	function captureScreenshot(): string | null {
		if (!renderer || !scene || !camera) return null;
		renderer.render(scene, camera);
		return renderer.domElement.toDataURL('image/png');
	}

	onMount(() => {
		scene = new THREE.Scene();
		scene.background = new THREE.Color(0x0f1219);
		camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.1, 10000);
		camera.position.set(200, 200, 200);
		renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
		renderer.setSize(container.clientWidth, container.clientHeight);
		renderer.setPixelRatio(window.devicePixelRatio);
		container.appendChild(renderer.domElement);
		controls = new OrbitControls(camera, renderer.domElement);
		controls.enableDamping = true;
		const ambientLight = new THREE.AmbientLight(0x888888);
		scene.add(ambientLight);
		const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
		directionalLight.position.set(1, 1, 1);
		scene.add(directionalLight);
		const grid = new THREE.GridHelper(1000, 20, 0x1e293b, 0x1e293b);
		scene.add(grid);

		// Fetch file with auth headers, then parse
		const s = get(session);
		const fetchHeaders: Record<string, string> = {};
		if (s?.access_token) {
			fetchHeaders['Authorization'] = `Bearer ${s.access_token}`;
		}
		fetch(fileUrl, { headers: fetchHeaders })
			.then(r => r.arrayBuffer())
			.then(buffer => {
				const loader = new ThreeMFLoader();
				const object = loader.parse(buffer);
				const box = new THREE.Box3().setFromObject(object);
				const center = box.getCenter(new THREE.Vector3());
				object.position.sub(center);
				object.traverse((child: THREE.Object3D) => {
					if (child instanceof THREE.Mesh) {
						child.material = new THREE.MeshPhongMaterial({ color: 0xb88c5a });
					}
				});
				scene.add(object);
				const size = box.getSize(new THREE.Vector3());
				const maxDim = Math.max(size.x, size.y, size.z);
				camera.position.set(maxDim, maxDim, maxDim);
				controls.target.set(0, 0, 0);
				controls.update();
			})
			.catch(err => console.error('Failed to load 3MF:', err));

		function animate() {
			animationId = requestAnimationFrame(animate);
			controls.update();
			renderer.render(scene, camera);
		}
		animate();

		api = { captureScreenshot };

		const resizeObserver = new ResizeObserver(() => {
			camera.aspect = container.clientWidth / container.clientHeight;
			camera.updateProjectionMatrix();
			renderer.setSize(container.clientWidth, container.clientHeight);
		});
		resizeObserver.observe(container);
		return () => { resizeObserver.disconnect(); };
	});

	onDestroy(() => {
		if (animationId) cancelAnimationFrame(animationId);
		if (renderer) renderer.dispose();
	});
</script>

<div bind:this={container} class="w-full h-80 rounded-lg border border-[var(--color-border)] overflow-hidden bg-[var(--color-bg)]"></div>
