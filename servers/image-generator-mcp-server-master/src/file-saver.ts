import * as fs from 'fs';
import * as path from 'path';
import { homedir } from 'os';

export class FileSaver {
    constructor(private dirPath: string) {
        if (!fs.existsSync(dirPath)) {
            fs.mkdirSync(dirPath, { recursive: true });
        }
    }

    async saveBase64(filename: string, base64String: string) {
        const buffer = Buffer.from(base64String, "base64");
        return this.save(filename, buffer);
    }
    
    async save(filename: string, content: Buffer | string)
    {
        filename = FileSaver.sanitizeFilename(filename);
        let filePath = path.join(this.dirPath, filename);

        // Check if the file already exists, and rename if necessary
        if (fs.existsSync(filePath)) {
            const ext = path.extname(filename); // File extension
            const baseName = path.basename(filename, ext); // Filename without extension
            const isoDate = new Date().toISOString().replace(/:/g, '-'); // ISO string, replace ':' to make it filename-safe
            filePath = path.join(this.dirPath, `${baseName}-${isoDate}${ext}`);
        }

        await fs.promises.writeFile(filePath, content);
        return filePath;
    }

    private static sanitizeFilename(filename: string): string {
        // Regular expression to match invalid characters for filenames across platforms
        const invalidCharacters = /[<>:"/\\|?*\x00-\x1F]/g;
    
        // Replace invalid characters with an empty string and trim trailing periods/spaces
        const sanitized = filename
            .replace(invalidCharacters, '') // Remove invalid characters
            .replace(/\.+$/, '')           // Remove trailing periods
            .trim();                       // Remove trailing spaces
    
        return sanitized;
    }

    static CreateDesktopFileSaver(directory: string) {
        directory = FileSaver.sanitizeFilename(directory);
        const desktopPath = path.join(homedir(), 'Desktop');
        const dirPath = path.join(desktopPath, directory);
        return new FileSaver(dirPath);
    }
}