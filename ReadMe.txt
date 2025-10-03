可以看當下路徑的使用硬碟量
du -sh *

models 的位置
~/.cache/huggingface/hub/models--FreedomIntelligence--HuatuoGPT-o1-7B

nohup python3 disaese_server.py &

python3 disaese_client.py -f classified_section_卷228.xlsx 

python3 disaese_client.py -f classified_section_卷345.xlsx -f classified_section_卷346.xlsx -f classified_section_卷347.xlsx -f classified_section_卷348.xlsx -f classified_section_卷349.xlsx -f classified_section_卷350.xlsx -f classified_section_卷351.xlsx -f classified_section_卷352.xlsx -f classified_section_卷353.xlsx -f classified_section_卷354.xlsx -f classified_section_卷355.xlsx

python3 disaese_client.py -f classified_section_卷345.xlsx -f classified_section_卷346.xlsx -f classified_section_卷347.xlsx -f classified_section_卷348.xlsx -f classified_section_卷349.xlsx -f classified_section_卷350.xlsx -f classified_section_卷351.xlsx -f classified_section_卷352.xlsx -f classified_section_卷353.xlsx -f classified_section_卷354.xlsx -f classified_section_卷355.xlsx

# Prompt 模板 / Prompt Template , 做暫存記錄一下

  prompt_template:
    "
    參考上下文：{context_paragraph}

    請將以下古文翻譯成現代中文，只需要翻譯文字含義，不要添加藥方、做法或任何額外說明：
    「{term}」

    翻譯：
    "

  prompt_template:
    "你是專業的古文中醫翻譯AI，不是中醫師，所以你只能專注翻譯古文。

    這是參考上下文：{context_paragraph}。

    這是需要翻譯的內容：「{term}」。

    你必須遵守：
    1.只做翻譯成繁體現代白話文。
    2.不能做解釋和建議，要有專業證照的中醫師才可以做解釋和建議。
    3.遇到中醫草藥名稱則跳過。"

  prompt_template:
    "將古文翻譯成現代白話文。只翻譯，不解釋，不添加任何內容。

    參考上下文：{context_paragraph}

    翻譯：「{term}」

    要求：直接翻譯成現代白話文，繁體中文，不要任何解釋或建議。"

  prompt_template:
    "
    將古代中醫文本翻譯成現代白話文。嚴格按照原文內容翻譯，不要添加任何原文沒有的內容。

    --- 參考上下文 ---
    {context_paragraph}
    --- 上下文結束 ---

    請將以下文本翻譯成現代白話文：
    「{term}」

    翻譯規則：
    1. 只翻譯原文實際包含的內容
    2. 不要添加任何治療方法、建議或解釋
    3. 不要擴展或補充原文沒有的信息
    4. 如果原文只是症狀描述，翻譯結果也只能是症狀描述
    5. 絕對禁止添加藥方、治療步驟或醫療建議
    6. 保持翻譯簡潔明了，只能使用繁體中文做輸出
    "


 