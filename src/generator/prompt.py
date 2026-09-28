from models import FileType, Prompts


class PromptHelper:

    @staticmethod
    def build_system_prompt(context: str, filetype: FileType):
        prompt = (
            f"""
    You are an expert file organization system. Your sole job is to rewrite messy, disorganized media filenames into perfectly structured, standardized versions.
    
    Use the following patterns and examples as a direct reference for your formatting decisions:
    {context}
    """
        )
        if filetype != FileType.SEASON:
            prompt += Prompts.EXTENSION.value
        if filetype == FileType.EPISODE:
            prompt += Prompts.EPISODE.value
        if filetype == FileType.SEASON:
            prompt += Prompts.SEASON.value
        if filetype in (FileType.TITLE, FileType.MOVIE):
            prompt += Prompts.TITLE.value
        prompt += Prompts.CRITICAL.value
        return prompt

    @staticmethod
    def build_prompt(filename: str, filetype: FileType, title_name: str = "") -> str:
        prompt = (
            f"""
    Analyze this file name and generate a short, cleaned name.  
    Name: {filename}          
    """
        )
        if filetype == FileType.EPISODE and title_name.strip():
            prompt += f"\nThe output MUST start with this exact string, character for character: {title_name}"
            prompt += "\nDo NOT re-capitalize, re-case, translate, reorder, or otherwise alter it. Append the episode token (and the extension, if any) after it, even if the input name is already correctly formatted."
        return prompt
