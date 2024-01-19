import argparse
import os
import base64
import re
from openai import OpenAI
import subprocess

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def edit_file(filepath, initial_message):
    editor = os.environ.get("EDITOR", "vim")  # that easy!
    with open(filepath, "w+") as tf:
        tf.write(initial_message)
        tf.flush()
        subprocess.run([editor, tf.name])
        tf.seek(0)
        return tf.read()


def query_ai(messages):
    while True:
        messages = [
            {
                # hyponotize the AI if necessary...
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "",
                    }
                ],
            }
        ] + messages
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="gpt-4-vision-preview",
            max_tokens=1000,
        )
        content = chat_completion.choices[0].message.content
        if not ("I'm sorry," in content):
            return chat_completion.choices[0].message.content
        else:
            print(f"Request rejected by AI with '{content}'. Retrying...")


def generate_instruction(image, hint):
    instruction = query_ai(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"Describe this picture as a figure to be used in a computer science conference. List all components as if you are preparing to draw the figure formally to present in a conference. Identify all handwritings. The hint of the figure from the user is {hint}",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image}"},
                    },
                ],
            }
        ]
    )
    return instruction


def generate_latex_code(image, instruction):
    while True:
        code_generation = query_ai(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Use TikZ to recreate this picture as a figure to be used in a computer science conference following the instruction below vetted by the user. Output only complete LaTeX code with standalone documentclass. Import tikz and all the necessary tikz libraries. Do not output anything else, as your answer will be fed into the LaTeX compiler.\n\n{instruction}",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image}"},
                        },
                    ],
                }
            ]
        )

        latex_search = re.search(r"(?s)```latex(.*)```", code_generation)

        if latex_search:
            latex_code = latex_search.group(1)
            print("----LaTeX----")
            print(latex_code)
            print("----LaTeX----")
            return latex_code


def critique_latex_code(image, instruction, output, code):
    critique = query_ai(
        [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"The following LaTeX Tikz code\n\n```{code}```\n\nis used to render the first hand-drawn figure to be used in a computer science conference with this user instruction\n\n```{instruction}```\n\nThe result image is the second figure. How do you improve the code so that the content of the second figure more closely matches the content of the first figure? Remember to imitate the content of the first figure but not the hand-drawn style to keep the figure formal to present in the conference. Output in bullet points and do not output the full LaTeX code, because the user will read your output and edit it.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image}"},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{output}"},
                    },
                ],
            }
        ]
    )
    return critique


def regenerate_latex_code(image, instruction, output, code, critique):
    while True:
        code_generation = query_ai(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"The following LaTeX Tikz code\n\n```{code}```\n\nis used to render the first hand-drawn figure to be used in a computer science conference with this user instruction\n\n```{instruction}```\n\nThe result image is the second figure. The user provided the following feedback\n\n```{critique}```\n\nEdit and output the edited code. Output only complete LaTeX code with standalone documentclass. Import tikz and all the necessary tikz libraries. Do not output anything else, as your answer will be fed into the LaTeX compiler.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image}"},
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{output}"},
                        },
                    ],
                }
            ]
        )

        latex_search = re.search(r"(?s)```latex(.*)```", code_generation)

        if latex_search:
            latex_code = latex_search.group(1)
            print("----LaTeX----")
            print(latex_code)
            print("----LaTeX----")
            return latex_code


def correct_compile_error(code, log):
    while True:
        code_generation = query_ai(
            [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"The following LaTeX code\n\n{code}\n\nhas run into this compile error\n\n{log}\n\n. Identify the error. Then produce the corrected code. Use only one code block, as it will be extracted as the corrected code.",
                        }
                    ],
                }
            ]
        )

        latex_search = re.search(r"(?s)```latex(.*)```", code_generation)

        if latex_search:
            latex_code = latex_search.group(1)
            print("----LaTeX----")
            print(latex_code)
            print("----LaTeX----")
            return latex_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generates TikZ code from image with AI.",
    )

    parser.add_argument("filename", help="file name of the image")
    parser.add_argument(
        "--hint", type=str, help="a short hint that guides the generation", default=""
    )
    parser.add_argument(
        "--continue", type=int, help="continue from this iteration", default=0
    )

    args = parser.parse_args()

    dirname = os.path.dirname(__file__)

    original_image = encode_image(args.filename)

    iteration = getattr(args, "continue")
    if iteration > 0:
        with open(f"{dirname}/tmp/instruction", "r") as f:
            instruction = f.read()
        with open(f"{dirname}/tmp/figure-{iteration}.tex", "r") as f:
            latex_code = f.read()
        with open(f"{dirname}/tmp/figure-{iteration}.critique", "r") as f:
            critique = f.read()
    else:
        instruction = generate_instruction(original_image, hint=args.hint)
        instruction = edit_file(f"{dirname}/tmp/instruction", instruction)
        if instruction == "":
            exit(0)
        latex_code = ""
        critique = ""

    print("----INSTRUCTION----")
    print(instruction)
    print("----INSTRUCTION----")

    while True:
        if iteration == 0:
            latex_code = generate_latex_code(
                image=original_image, instruction=instruction
            )
        else:
            latex_code = regenerate_latex_code(
                image=original_image,
                instruction=instruction,
                output=output,
                code=latex_code,
                critique=critique,
            )

        while True:
            with open(f"{dirname}/tmp/figure-{iteration}.tex", "w") as f:
                f.write(latex_code)

            compile_attempt = subprocess.run(
                [
                    "dvilualatex",
                    f"--output-directory={dirname}/tmp/",
                    f"--interaction=nonstopmode",
                    f"--halt-on-error",
                    f"{dirname}/tmp/figure-{iteration}.tex",
                ]
            )

            # hope it compiles...
            if compile_attempt.returncode == 0:
                break

            with open(f"{dirname}/tmp/figure-{iteration}.log", "r") as f:
                log = f.read()
                latex_code = correct_compile_error(latex_code, log)

        subprocess.run(
            [
                "dvisvgm",
                "--no-fonts",
                f"--output={dirname}/tmp/figure-{iteration}.svg",
                f"{dirname}/tmp/figure-{iteration}.dvi",
            ],
            check=True,
        )

        subprocess.run(
            [
                "convert",
                f"{dirname}/tmp/figure-{iteration}.svg",
                f"{dirname}/tmp/figure-{iteration}.png",
            ],
            check=True,
        )

        output = encode_image(f"{dirname}/tmp/figure-{iteration}.png")
        critique = critique_latex_code(original_image, instruction, output, latex_code)
        critique = edit_file(f"{dirname}/tmp/figure-{iteration}.critique", critique)
        if critique == "":
            exit(0)

        print("----CRITIQUE----")
        print(critique)
        print("----CRITIQUE----")

        iteration = iteration + 1
