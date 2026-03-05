def word_splitter(text):
    """
    全方位拆解邏輯：
    1. 針對常見助詞進行精準拆分。
    2. 確保「ありがとうございます」這類長詞不被切碎。
    3. 標點符號獨立成塊。
    """
    text = text.strip()
    # 這裡加入你發現會被切錯的長單字，進行優先保護
    protected_words = ['ありがとうございます', 'ありがとうございました', 'すみません', 'ごめんなさい']
    for word in protected_words:
        # 暫時把長單字替換成特殊標記，避免被助詞邏輯切開
        text = text.replace(word, f"___{word}___")

    # 定義要拆開的助詞
    particles = ['は', 'が', 'を', 'に', 'へ', 'と', 'も', 'で', 'の', 'から', 'まで']
    # 定義標點
    punctuations = ['、', '。', '！', '？']
    
    # 建立拆分正則 (捕捉助詞與標點)
    pattern = f"({'|'.join(particles + punctuations)})"
    
    # 先初步切分
    raw_parts = re.split(pattern, text)
    
    # 還原被保護的長單字並過濾空值
    tokens = []
    for p in raw_parts:
        if p.startswith("___") and p.endswith("___"):
            tokens.append(p.replace("___", ""))
        elif p and p.strip():
            tokens.append(p)
            
    return tokens
