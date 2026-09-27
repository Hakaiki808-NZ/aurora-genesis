from genesis import Genesis

print("Genesis v0.1 — type /state, /trace <message>, or /quit")
with Genesis() as a:
    while True:
        try: text=input("YOU> ").strip()
        except (EOFError,KeyboardInterrupt): break
        if not text: continue
        if text=="/quit": break
        if text=="/state": print(a.state()); continue
        if text.startswith("/trace "): print(a.respond_with_trace(text[7:])); continue
        print("GENESIS>",a.respond(text))
