import { execSync } from "child_process";
import fs from "fs";
import path from "path";

console.log("--- Building Dashboard ---");
execSync("npm exec vite build", { stdio: "inherit" });

const gamesDir = "./games";
if (fs.existsSync(gamesDir)) {
	const games = fs.readdirSync(gamesDir).filter((file) => {
		return fs.statSync(path.join(gamesDir, file)).isDirectory();
	});

	games.forEach((gameDirName) => {
		const gamePath = path.join(gamesDir, gameDirName);
		const targetDistPath = path.join("./dist/games", gameDirName);
		console.log(`Copying static game: [${gameDirName}]...`);
		fs.cpSync(gamePath, targetDistPath, { recursive: true });
	});
}

console.log("--- Done ---");
