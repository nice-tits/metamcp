import OpenAI from "openai";
import { ImageGenerateParams } from "openai/resources/images.mjs";

const IMAGE_MODEL = "dall-e-3";

export class ImageGenerator {
    private openai: OpenAI;
    constructor(apiKey:string = process.env.OPENAI_API_KEY!) {
        this.openai = new OpenAI({ apiKey });
    }

    async generateImage(prompt: string, size: ImageGenerateParams['size'] = "1024x1024") {
        const response = await this.openai.images.generate({
            model: IMAGE_MODEL,
            prompt,
            size,
            response_format: 'b64_json'
        });
        return response.data[0].b64_json;
    }
}