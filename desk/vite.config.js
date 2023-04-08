import path from "path";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import Icons from "unplugin-icons/vite";
import { FileSystemIconLoader } from "unplugin-icons/loaders";
import svgLoader from "vite-svg-loader";
import { getProxyOptions } from "frappe-ui/src/utils/vite-dev-server";
import { webserver_port } from "../../../sites/common_site_config.json";

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [
		vue(),
		svgLoader(),
		Icons({
			compiler: "vue3",
			customCollections: {
				espresso: FileSystemIconLoader("./src/assets/icons", (svg) =>
					svg.replace(/^<svg /, '<svg fill="currentColor" ')
				),
			},
		}),
	],
	server: {
		port: 8080,
		proxy: getProxyOptions({ port: webserver_port }),
	},
	resolve: {
		alias: {
			"@": path.resolve(__dirname, "src"),
		},
	},
	build: {
		outDir: `../helpdesk/public/desk`,
		emptyOutDir: true,
		target: "es2021",
	},
	optimizeDeps: {
		include: ["feather-icons", "showdown"],
	},
});
