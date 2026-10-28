import streamlit as st

def render_sala_di_guerra():
    st.title("MattHammer — Sala di Guerra")
    st.caption("Costruttore d'armata, bilancio ruoli (Mago, Sacerdote, Eroe), controllo punti e analisi match-up.")

    with st.container(border=True):
        st.subheader("Seleziona Formato Battaglia")
        st.caption("Imposta il limite punti della partita per monitorare la composizione del tuo schieramento.")
        
        c1, c2 = st.columns(2)
        formato = c1.selectbox("Formato Partita", ["Path to Glory (600 pt)", "Vanguard (1000 pt)", "Strike Force (1500 pt)", "Battlehost (2000 pt)", "Personalizzato"])
        limite_punti = 1000
        if "600" in formato: limite_punti = 600
        elif "1000" in formato: limite_punti = 1000
        elif "1500" in formato: limite_punti = 1500
        elif "2000" in formato: limite_punti = 2000
        else: limite_punti = c2.number_input("Punti Massimi", value=1000, step=50)

        st.info(f"Limite impostato a **{limite_punti} punti**. Il costruttore del roster con analisi delle carenze della lista verrà integrato qui.")