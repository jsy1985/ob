import streamlit as st
from openai import OpenAI
from PIL import Image
import io
import base64
import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 환경변수에서 API 키 가져오기
API_KEY = st.secrets["API_KEY"] if "API_KEY" in st.secrets else os.getenv("API_KEY")

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "yumc":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # 비밀번호 입력 필드 삭제
        else:
            st.session_state["password_correct"] = False

    # First run 또는 비밀번호가 틀린 경우
    if "password_correct" not in st.session_state:
        st.text_input(
            "비밀번호를 입력하세요", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("올바른 비밀번호를 입력해주세요")
        return False
    
    # 비밀번호가 틀린 경우
    elif not st.session_state["password_correct"]:
        st.text_input(
            "비밀번호를 입력하세요", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("비밀번호가 틀렸습니다. 다시 시도해주세요.")
        return False
    
    # 비밀번호가 맞은 경우
    else:
        return True



def main():
    st.set_page_config(page_title="Ocular biometry", layout="wide")
    st.title("Ocular biometry")

    if check_password():  # 비밀번호 확인
        col1, col2 = st.columns([3, 1])
        with col1:
            st.text_input("파일 경로 표시", disabled=True)
        with col2:
            uploaded_file = st.file_uploader("File upload", type=['jpg', 'jpeg', 'png'])

        if uploaded_file:
            if st.button("Extract Parameters") or 'current_params' not in st.session_state:
                image = Image.open(uploaded_file)
                params = extract_parameters(image)
                if params:
                    st.session_state.current_params = params

            if 'current_params' in st.session_state:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**OD**")
                    st.number_input("AL:", value=float(st.session_state.current_params['OD']['AL']), format="%.2f", key="od_al", on_change=update_params)
                    st.number_input("ACD:", value=float(st.session_state.current_params['OD']['ACD']), format="%.2f", key="od_acd", on_change=update_params)
                    st.number_input("K1:", value=float(st.session_state.current_params['OD']['K1']), format="%.2f", key="od_k1", on_change=update_params)
                    st.number_input("K2:", value=float(st.session_state.current_params['OD']['K2']), format="%.2f", key="od_k2", on_change=update_params)
                    st.write(f"K (SE): {calculate_se(st.session_state.current_params['OD']['K1'], st.session_state.current_params['OD']['K2']):.2f}")

                with col2:
                    st.markdown("**OS**")
                    st.number_input("AL:", value=float(st.session_state.current_params['OS']['AL']), format="%.2f", key="os_al", on_change=update_params)
                    st.number_input("ACD:", value=float(st.session_state.current_params['OS']['ACD']), format="%.2f", key="os_acd", on_change=update_params)
                    st.number_input("K1:", value=float(st.session_state.current_params['OS']['K1']), format="%.2f", key="os_k1", on_change=update_params)
                    st.number_input("K2:", value=float(st.session_state.current_params['OS']['K2']), format="%.2f", key="os_k2", on_change=update_params)
                    st.write(f"K (SE): {calculate_se(st.session_state.current_params['OS']['K1'], st.session_state.current_params['OS']['K2']):.2f}")

                if st.button("Analyze biometry"):
                    interpreter = BiometryInterpreter()
                    results = interpreter.analyze(st.session_state.current_params)
                    st.write(results)

if __name__ == "__main__":
    main()
