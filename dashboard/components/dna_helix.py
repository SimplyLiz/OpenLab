"""Three.js 3D DNA helix visualization as Streamlit HTML component."""

import streamlit as st
import streamlit.components.v1 as components


def render_dna_helix(height: int = 400):
    """Render an animated 3D DNA helix using Three.js."""
    html = f"""
    <div id="helix-container" style="width:100%;height:{height}px;"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
    (function() {{
        const container = document.getElementById('helix-container');
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0e1117);
        const camera = new THREE.PerspectiveCamera(60, container.clientWidth / {height}, 0.1, 1000);
        camera.position.set(0, 0, 30);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setSize(container.clientWidth, {height});
        container.appendChild(renderer.domElement);

        const group = new THREE.Group();
        scene.add(group);

        const basePairColors = [0x2ecc71, 0xe74c3c, 0x3498db, 0xf39c12];
        const helixRadius = 5;
        const turns = 4;
        const pointsPerTurn = 20;
        const totalPoints = turns * pointsPerTurn;
        const ySpread = 40;

        for (let i = 0; i < totalPoints; i++) {{
            const t = i / totalPoints;
            const angle = t * turns * Math.PI * 2;
            const y = (t - 0.5) * ySpread;

            // Strand 1
            const x1 = Math.cos(angle) * helixRadius;
            const z1 = Math.sin(angle) * helixRadius;
            const sphere1 = new THREE.Mesh(
                new THREE.SphereGeometry(0.3, 8, 8),
                new THREE.MeshPhongMaterial({{ color: 0x3498db }})
            );
            sphere1.position.set(x1, y, z1);
            group.add(sphere1);

            // Strand 2
            const x2 = Math.cos(angle + Math.PI) * helixRadius;
            const z2 = Math.sin(angle + Math.PI) * helixRadius;
            const sphere2 = new THREE.Mesh(
                new THREE.SphereGeometry(0.3, 8, 8),
                new THREE.MeshPhongMaterial({{ color: 0xe74c3c }})
            );
            sphere2.position.set(x2, y, z2);
            group.add(sphere2);

            // Base pair connector
            if (i % 2 === 0) {{
                const color = basePairColors[i % 4];
                const material = new THREE.MeshPhongMaterial({{ color }});
                const geometry = new THREE.CylinderGeometry(0.1, 0.1, helixRadius * 2, 4);
                const connector = new THREE.Mesh(geometry, material);
                connector.position.set((x1 + x2) / 2, y, (z1 + z2) / 2);
                connector.lookAt(x1, y, z1);
                connector.rotateX(Math.PI / 2);
                group.add(connector);
            }}
        }}

        const ambientLight = new THREE.AmbientLight(0x404040, 2);
        scene.add(ambientLight);
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(10, 10, 10);
        scene.add(directionalLight);

        function animate() {{
            requestAnimationFrame(animate);
            group.rotation.y += 0.005;
            renderer.render(scene, camera);
        }}
        animate();
    }})();
    </script>
    """
    components.html(html, height=height)
