"""測試共用：題目範例與對應的「正確」模型輸出。"""

S1 = "我在 10/12 訂的訂單 A20261012-5531，買了兩件外套，結果只收到一件，請盡快補寄，不然我要退貨。"
S2 = "上週買的吹風機用兩天就壞了，我要退款。訂單號碼我找不到了。"
S3 = "請問你們的會員點數什麼時候會到期？順便問一下我上次訂單 B88812 為什麼還沒出貨。"

VALID = {
    "s1": (S1, {
        "categories": ["missing_item"], "categories_evidence": "只收到一件",
        "order_id": "A20261012-5531", "order_id_evidence": "訂單 A20261012-5531",
        "request": "補寄少收的外套", "request_evidence": "請盡快補寄",
        "urgency": "high", "urgency_evidence": "盡快",
    }),
    "s2": (S2, {
        "categories": ["defective"], "categories_evidence": "用兩天就壞了",
        "order_id": None, "order_id_evidence": None,
        "request": "退款", "request_evidence": "我要退款",
        "urgency": "normal", "urgency_evidence": None,
    }),
    "s3": (S3, {
        "categories": ["membership", "shipping_delay"], "categories_evidence": "會員點數",
        "order_id": "B88812", "order_id_evidence": "訂單 B88812",
        "request": "詢問點數到期日與出貨進度", "request_evidence": "請問",
        "urgency": "normal", "urgency_evidence": None,
    }),
}
