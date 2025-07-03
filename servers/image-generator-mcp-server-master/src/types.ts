export interface ImageGenerationRequestParams {
    prompt: string;
    imageName: string;
}

export function isValidImageGenerationArgs(args: any): args is ImageGenerationRequestParams {
    return typeof args === "object" &&
        args !== null &&
        "prompt" in args &&
        typeof args.prompt === 'string' &&
        "imageName" in args &&
        typeof args.imageName === 'string';  
}