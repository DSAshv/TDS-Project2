# requires-python = ">=3.11"
# dependencies = [
#   "json",
#   "pandas",
#   "ydata-profiling",
#   "re",
#   "os",
#   "matplotlib",
#   "seaborn"
# ]

import argparse
import os

def install_packages(packages):
    for package in packages:
        install_package(package)

# List of required packages
required_packages = ['ydata-profiling', 'pandas', 'seaborn', 'matplotlib']
install_packages(required_packages)

import pandas as pd
from ydata_profiling import ProfileReport
import re
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib
import numpy as np
matplotlib.use('Agg')

def process_json(data, threshold=510, sub_json_threshold=10):
    """
    Filters and processes a JSON object to remove unwanted keys and large sub-objects.

    Args:
        data (dict): The JSON data to process.
        threshold (int): The maximum allowed size for sub-objects.
        sub_json_threshold (int): The threshold for listing sub-objects.

    Returns:
        dict: The filtered JSON data.
    """
    allowed_keys = ['n_distinct', 'p_distinct', 'is_unique', 'n_unique', 'p_unique', 'type', 
                    'hashable', 'ordering', 'n_missing', 'n', 'p_missing', 'count', 'memory_size', 
                    'first_rows', 'max_length', 'mean_length', 'median_length', 'min_length', 
                    'n_characters_distinct', 'n_characters', 'n_negative', 'p_negative', 'n_infinite', 
                    'n_zeros', 'mean', 'std', 'variance', 'min', 'max', 'kurtosis', 'skewness', 'sum', 
                    'mad', 'chi_squared', 'statistic', 'pvalue', 'range', '5%', '25%', '50%', '75%', 
                    '95%', 'iqr', 'cv', 'p_zeros', 'p_infinite', 'monotonic_increase', 
                    'monotonic_decrease', 'monotonic_increase_strict', 'monotonic_decrease_strict', 
                    'monotonic', 'cast_type']

    def filter_json(data):
        if isinstance(data, dict):
            if 'variables' in data:
                data['variables'] = {k: {sub_k: sub_v for sub_k, sub_v in v.items() if sub_k in allowed_keys} 
                                     for k, v in data['variables'].items()}
            return {k: filter_json(v) for k, v in data.items() if k not in ["missing", "value_counts_without_nan", "value_counts_index_sorted", "histogram", "scatter", "analysis", "sample", "package", "duplicates", "bar", "matrix", "time_index_analysis"] and not (isinstance(v, (dict, list)) and len(v) > threshold)}
        elif isinstance(data, list):
            return [filter_json(item) for item in data if not (isinstance(item, (dict, list)) and len(item) > threshold)]
        else:
            return data

    def list_sub_json(data):
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)) and len(v) > sub_json_threshold:
                    print(f"Key: {k}, Number of values: {len(v)}")
                list_sub_json(v)
        elif isinstance(data, list):
            for item in data:
                list_sub_json(item)

    try:
        filtered_data = filter_json(data)
        list_sub_json(filtered_data)
        return filtered_data
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def load_dataset(file_path):
    """
    Loads a dataset from a CSV file.

    Args:
        file_path (str): The path to the CSV file.

    Returns:
        tuple: A tuple containing the DataFrame and an error message (if any).
    """
    if not os.path.exists(file_path):
        return None, f"Error: File {file_path} does not exist."
    try:
        return pd.read_csv(file_path), None
    except Exception as e:
        return None, f"Error loading CSV file: {e}"

def basic_analysis(df):
    """
    Performs basic analysis on a DataFrame.

    Args:
        df (DataFrame): The DataFrame to analyze.

    Returns:
        tuple: A tuple containing the analysis summary and an error message (if any).
    """
    try:
        summary = {
            "head": df.head().to_dict(),
            "description": df.describe(include='all').to_dict(),
            "null_counts": df.isnull().sum().to_dict()
        }
        return summary, None
    except Exception as e:
        return None, f"Error during basic analysis: {e}"

def get_llm_insights(prompt, max_tokens=1000):
    """
    Interacts with an API endpoint to get insights from a language model.

    Args:
        prompt (str): The prompt to send to the API.
        max_tokens (int): The maximum number of tokens to generate.

    Returns:
        tuple: A tuple containing the response string and an error message (if any).
    """
    try:
        import http.client

        conn = http.client.HTTPSConnection("aiproxy.sanand.workers.dev")
        headers = {
            "Authorization": f"Bearer {os.getenv('AIPROXY_TOKEN')}",
            "Content-Type": "application/json"
        }
        payload = json.dumps({
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        })
        conn.request("POST", "/openai/v1/chat/completions", payload, headers)
        response = conn.getresponse()
        data = response.read().decode("utf-8")
        response_json = json.loads(data)
        response_str = response_json["choices"][0]["message"]["content"].strip()
        return response_str, None
    except Exception as e:
        return None, f"Error fetching insights from API endpoint: {e}"

def generate_story_with_visuals(finalString):
    """
    Generates a professional narrative with visuals based on analysis.

    Args:
        finalString (str): The analysis string to base the narrative on.

    Returns:
        tuple: A tuple containing the story and an error message (if any).
    """
    prompt = (
        f"Instructions to follow:"
        f"Create a professional narrative based on the following analysis. "
        f"Start with a catchy title, then describe the dataset, and an overview of the analysis performed. "
        f"Highlight key insights, their implications, and suggest actions based on these findings. "
        f"Include maximum three graphs in between the insights that best illustrate the insights points, and provide the code to generate these graphs in code block ```python(.*?)``` like this. 'data' is the dataframe of file variable. use only matplotlib.pyplot as plt and seaborn as sns. Each code will be executed separately so donot create dependent variables."
        f"Ensure the column names are accurate and the narrative is compelling. "
        f"Do not add any placeholders for graph. "
        f"Clearly structure the report with sections for Introduction, Analysis, Insights, Recommendations. These headings are must.\n\n"
        f"Analysis:\n{finalString}\n\n"
    )
    print("Final report.")
    story, error = get_llm_insights(prompt, max_tokens=2000)
    if error:
        return f"Error generating story: {error}", None
    return story, error

def generate_questions_and_analyze(df, profile_json):
    """
    Generates targeted questions and analyzes the dataset with AI.

    Args:
        df (DataFrame): The DataFrame to analyze.
        profile_json (dict): The JSON profile of the dataset.

    Returns:
        str: The generated story with insights.
    """
    basic = basic_analysis(df)
    
    question = "Based on the Table Information, context, Variables and Alerts generate 5 interesting sub-questions separated by commas ended by '?', that can help predict future trends based on the dataset."
    question +="Additionally, select variable names for each question which can help to find answers for the question. Provide the variable names as a list [] at the end."
    question += "do not return anything else."

    table_info = profile_json.get("table", {})
    variables_info = profile_json.get("variables", {}).keys()
    alerts_info = profile_json.get("alerts", [])

    prompt = (
        f"context:\n{basic}\n\n"
        f"Table Information:\n{table_info}\n\n"
        f"Variables:\n{', '.join(variables_info)}\n\n"
        f"Alerts:\n{alerts_info}\n\n"
        f"Question: {question}"
    )

    sub_questions_text, error = get_llm_insights(prompt)
    if error:
        return f"Error generating sub-questions: {error}"

    sub_questions = [q.strip() for q in sub_questions_text.split("?,") if q.strip()]

    detailed_responses = []

    for sub_question in sub_questions:
        if "[" in sub_question and "]" in sub_question:
            variables = sub_question[sub_question.index("[")+1:sub_question.index("]")].split(",")
            for var in variables:
                var = var.strip()
                if var in profile_json.get("variables", {}):
                    detailed_prompt = (
                        f"Summary from data: \n {var} : {profile_json['variables'][var]}\n\n"
                        f"Sub-question: {sub_question}"
                        f"Based on Summary from data answer the Sub-question analytically."
                    )

                    detailed_response, error = get_llm_insights(detailed_prompt)
                    if error:
                        pass
                    else:
                        detailed_responses.append(f"Question:{sub_question} \n Answer:{detailed_response.strip()}")

    detailed_analysis = "\n\n".join(detailed_responses)
    final_string = f"dataset:{basic}\nDetailed Analysis:\n{detailed_analysis}"
    story, error = generate_story_with_visuals(final_string)

    if error:
        print(error)
        return
    
    return story

def execute_graph_code(data, story, output_path):
    """
    Processes a story containing embedded Python code blocks, executes them,
    saves generated graphs, and replaces code blocks with image references.

    Args:
        data (DataFrame): The DataFrame to use for generating graphs.
        story (str): The story containing embedded Python code blocks.
        output_path (str): The directory to save generated graphs.

    Returns:
        tuple: A tuple containing the updated story and an error message (if any).
    """
    try:
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Output directory '{output_path}' does not exist.")

        code_blocks = re.findall(r'```python(.*?)```\s', story, re.DOTALL)

        if not code_blocks:
            raise ValueError("No Python code blocks found in the story.")

        image_paths = []

        for i, code_block in enumerate(code_blocks):
            try:
                clean_code = "\n".join(line.lstrip() for line in code_block.splitlines())

                image_filename = f"graph_{i + 1}.png"
                image_path = os.path.join(output_path, image_filename)
                image_paths.append(image_path)

                local_scope = {"plt": plt, "data": data, "df": data, "sns": sns, "np": np}
                exec(clean_code, globals(), local_scope)

                plt.savefig(image_path)
                plt.close()

            except Exception as e:
                print(f"Error executing code block {i + 1}: {e}")
                image_paths.append(None)
                continue

        for i, code_block in enumerate(code_blocks):
            image_markdown = f"![Graph {i + 1}]({image_paths[i]})" if image_paths[i] else f"[Error in Graph {i + 1}]\n"
            story = re.sub(
                re.escape(f'```python{code_block}```'),
                image_markdown,
                story,
                count=1
            )

        return story, None
    except Exception as e:
        return None, f"Error executing graph code: {e}"

def narrate_to_markdown(df, story, output_path):
    """
    Narrates findings to a Markdown file, including executing graph code.

    Args:
        df (DataFrame): The DataFrame to use for generating graphs.
        story (str): The story containing embedded Python code blocks.
        output_path (str): The directory to save the Markdown file.

    Returns:
        str: An error message (if any).
    """
    try:
        story, error = execute_graph_code(df, story, output_path)
        if error:
            return error

        readme_path = os.path.join(output_path, "README.md")
        with open(readme_path, "w") as f:
            if story:
                f.write(story + "\n")
        return None
    except Exception as e:
        return f"Error during Markdown narration: {e}"

def main():
    """
    Main function to execute the AI-powered dataset analysis agent.
    """
    parser = argparse.ArgumentParser(description="AI-Powered Dataset Analysis Agent")
    parser.add_argument("csv_file", help="Path to the CSV file")
    args = parser.parse_args()
    csv_file_path = args.csv_file

    if not os.path.isfile(csv_file_path):
        print(f"Error: File {csv_file_path} does not exist.")
        return

    df = pd.read_csv(csv_file_path, encoding='latin1')
    profile = ProfileReport(df, title="Pandas Profiling Report")
    import json
    profile_json_str = profile.to_json()
    profile_json = json.loads(profile_json_str)
    profile_json = process_json(profile_json)
    
    insights = generate_questions_and_analyze(df, profile_json)
    print(insights)

    error = narrate_to_markdown(df, insights, "./")
    if error:
        print(error)
        return

    print(f"Analysis complete.")

if __name__ == "__main__":
    main()
