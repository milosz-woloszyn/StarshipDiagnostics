from dotenv import load_dotenv
from openai import OpenAI


def main():
    load_dotenv(".env")

    client = OpenAI()

    messages=[
        {
            "role": "system",
            "content": "jesteś pompą ciepła odpowiadaj z powiedzeniami: Niech ciepło popłynie, gdy zima się zbliża!"

        },
    ]

    while True:
        imput_text = input("Please enter your imputation text: ")
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