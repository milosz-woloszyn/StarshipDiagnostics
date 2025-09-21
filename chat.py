from dotenv import load_dotenv
from openai import OpenAI


def main():
    load_dotenv(".env")

    client = OpenAI()

    personality = input("jaka ma być torzsamość chat'a")

    messages=[
        {
            "role": "system",
            "content": personality,

        },
    ]

    while True:
        imput_text = input("Please enter your imputation text: ")

        if imput_text == "/exit":
            break

        messages+=[{"role": "user","content": imput_text}]

        request = client.chat.completions.create(model="gpt-4o-mini",messages=messages)
        text = request.choices[0].message.content
        print(text)
        messages+=[
            {
                "role": "assistant", "content": text
            }
        ]



if __name__ == "__main__":
    main()