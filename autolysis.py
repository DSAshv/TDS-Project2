import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests
import json
from ydata_profiling import ProfileReport

def process_json(data, threshold=510, sub_json_threshold=10):
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
            return {k: filter_json(v) for k, v in data.items() if k not in ["value_counts_without_nan", "value_counts_index_sorted", "histogram", "scatter", "analysis", "sample", "package", "duplicates", "bar", "matrix", "time_index_analysis"] and not (isinstance(v, (dict, list)) and len(v) > threshold)}
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

# Function to load and validate dataset
def load_dataset(file_path):
    if not os.path.exists(file_path):
        return None, f"Error: File {file_path} does not exist."
    try:
        return pd.read_csv(file_path), None
    except Exception as e:
        return None, f"Error loading CSV file: {e}"

# Perform basic analysis
def basic_analysis(df):
    try:
        summary = {
            "head": df.head().to_dict(),
            "description": df.describe(include='all').to_dict(),
            "null_counts": df.isnull().sum().to_dict()
        }
        return summary, None
    except Exception as e:
        return None, f"Error during basic analysis: {e}"

# Generate visualizations
def generate_visualizations(df, output_dir):
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Correlation Heatmap
        heatmap_path = os.path.join(output_dir, "correlation_heatmap.png")
        plt.figure(figsize=(10, 8))
        sns.heatmap(df.select_dtypes(include='number').corr(), annot=True, cmap="coolwarm")
        plt.title("Correlation Heatmap")
        plt.savefig(heatmap_path)
        plt.close()

        # Null Value Count
        null_counts = df.isnull().sum()
        null_counts_path = None
        if null_counts.sum() > 0:
            null_counts_path = os.path.join(output_dir, "null_value_counts.png")
            null_counts[null_counts > 0].plot(kind="bar", figsize=(10, 6))
            plt.title("Null Value Counts")
            plt.savefig(null_counts_path)
            plt.close()

        # Distribution of Numeric Columns
        numeric_distributions_path = None
        numeric_cols = df.select_dtypes(include='number')
        if not numeric_cols.empty:
            numeric_distributions_path = os.path.join(output_dir, "numeric_distributions.png")
            numeric_cols.hist(figsize=(12, 10), bins=20)
            plt.suptitle("Distributions of Numeric Columns")
            plt.savefig(numeric_distributions_path)
            plt.close()

        return {
            "heatmap": heatmap_path,
            "null_counts": null_counts_path,
            "distributions": numeric_distributions_path
        }, None
    except Exception as e:
        return None, f"Error during visualization generation: {e}"

# Interact with API endpoint for insights
def get_llm_insights(prompt, max_tokens=1000):
    try:
        api_endpoint = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        headers = {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIyZjMwMDE2NjJAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.f565ymhpgn7zsGSjaPc2RHHgIHqYVu7Xxqw6l1XASKk",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens
        }

        print("Prompt: ", prompt)
        response = requests.post(api_endpoint, headers=headers, json=payload, timeout=20)
        response.raise_for_status()

        response_str = response.json()["choices"][0]["message"]["content"].strip()
        print("Response: ", response_str + "\n")
        
        return response_str, None
    except Exception as e:
        return None, f"Error fetching insights from API endpoint: {e}"

def generate_story_with_visuals(finalString):
    prompt = (
        f"Please create a professional and engaging narrative based on the following analysis. "
        f"Start with a brief introduction of the dataset and the analysis performed. "
        f"Highlight key insights and their implications, and suggest actions based on these findings. "
        f"Include up to three graphs that best illustrate the points, and provide the code to generate these graphs in square brackets. "
        f"Ensure the column names are accurate and the narrative is compelling.\n\n"
        f"Analysis:\n{finalString}\n\n"
    )
    story, error = get_llm_insights(prompt, max_tokens=2000)
    if error:
        return f"Error generating story: {error}", None
    return story, error


# Generate targeted questions and analyze with AI
def generate_questions_and_analyze(df):
    # Ask the 5th question to generate sub-questions
    context = []

    question = (
        "Based on the dataset summary and context, generate 4 interesting sub-questions separated by commas, that can help predict future trend based on dataset. Do not return anything else."
    )

    prompt = (
        f"context:\n{context}\n\n"
        f"Question: {question}"
    )

    sub_questions_text, error = get_llm_insights(prompt)
    if error:
        return f"Error generating sub-questions: {error}"

    # Split the sub-questions by commas
    sub_questions = [q.strip() for q in sub_questions_text.split(",") if q.strip()]

    # Answer each sub-question using the context of the first four questions
    detailed_responses = []
    context_text = "\n".join(context)
    for i, sub_question in enumerate(sub_questions, 1):
        detailed_prompt = (
            f"Context from previous answers:\n{context_text}\n\n"
            f"Sub-question {i}: {sub_question}"
        )
        detailed_response, error = get_llm_insights(detailed_prompt)
        if error:
            detailed_responses.append(f"Error for Sub-question {i}: {error}")
        else:
            detailed_responses.append(f"{i}. {detailed_response.strip()}")

    # Combine all responses
    insights = "\n".join(context)
    detailed_analysis = "\n".join(detailed_responses)
    final_string = f"Insights:\n{insights}\n\nSub-questions:\n{sub_questions_text}\n\nDetailed Analysis:\n{detailed_analysis}"

    story, error = generate_story_with_visuals(final_string)
    if error:
        print(error)
        return
    
    return story

# Narrate findings to README.md
def narrate_to_markdown(image_paths, story, output_path):
    try:
        readme_path = os.path.join(output_path, "README.md")
        with open(readme_path, "w") as f:
            f.write("## Visualization URLs\n")
            for key, path in image_paths.items():
                if path:
                    f.write(f"- {key.capitalize()}: ![View]({path})\n")
            if story:
                f.write(story + "\n")
        return None
    except Exception as e:
        return f"Error during Markdown narration: {e}"


# Main function
def main():
    # parser = argparse.ArgumentParser(description="AI-Powered Dataset Analysis Agent")
    # parser.add_argument("csv_file", help="Path to the CSV file")
    # parser.add_argument("output_dir", nargs="?", default="output", help="Directory to save the outputs (default: output)")
    # args = parser.parse_args()

    # Load dataset
    df, error = load_dataset("goodreads.csv")
    if error:
        print(error)
        return

    # Perform analysis
    analysis_summary, error = basic_analysis(df)
    if error:
        print(error)
        return
    
    profile = ProfileReport(df, title="Pandas Profiling Report")
    profile_json = profile.to_json()
    profile_json = process_json(profile_json)
    

    # Generate questions and analyze with AI
    insights = generate_questions_and_analyze(df)

    # Narrate findings
    error = narrate_to_markdown(image_paths, insights, "./")
    if error:
        print(error)
        return

    print(f"Analysis complete.")

if __name__ == "__main__":
    main()
