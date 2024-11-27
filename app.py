import streamlit as st
from openai import OpenAI
from PIL import Image
import io
import base64
import os
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 환경변수에서 API 키 가져오기 부분 수정
API_KEY = st.secrets.secrets.API_KEY if hasattr(st.secrets, "secrets") else os.getenv("API_KEY")



class BiometryInterpreter:
    def __init__(self):
        self.interpretations = {
            'OD': [],
            'OS': []
        }
    
    def analyze(self, params):
        self.analyze_AL('OD', params['OD']['AL'])
        self.analyze_AL('OS', params['OS']['AL'])
        self.analyze_ACD('OD', params['OD']['ACD'])
        self.analyze_ACD('OS', params['OS']['ACD'])
        self.analyze_SE('OD', params['OD']['K (SE)'])
        self.analyze_SE('OS', params['OS']['K (SE)'])
        self.analyze_astigmatism('OD', params['OD']['K1'], params['OD']['K2'])
        self.analyze_astigmatism('OS', params['OS']['K1'], params['OS']['K2'])
        self.analyze_bilateral_differences(params['OD'], params['OS'])
        return self.get_report()

    def analyze_AL(self, eye, value):
        if value < 22.0:
            self.interpretations[eye].append(f"AL({value:.2f}mm)이 짧은 short eye입니다.")
        elif value > 26.0:
            self.interpretations[eye].append(f"AL({value:.2f}mm)이 긴 long eye입니다.")

    def analyze_ACD(self, eye, value):
        if value < 2.2:
            self.interpretations[eye].append(f"전방각({value:.2f}mm)이 매우 좁습니다. 술전 처치나 core vitrectomy를 고려하십시오.")
        elif value < 2.5:
            self.interpretations[eye].append(f"전방각({value:.2f}mm)이 좁습니다.")

    def analyze_SE(self, eye, value):
        if value < 41:
            self.interpretations[eye].append(f"각막굴절률({value:.2f}D)이 낮습니다. 굴절수술력을 확인하세요.")
        elif value > 47:
            self.interpretations[eye].append(f"각막굴절률({value:.2f}D)이 높습니다. 원추각막을 확인하세요.")

    def analyze_astigmatism(self, eye, k1, k2):
        astig = abs(k2 - k1)
        if astig > 1.5:
            self.interpretations[eye].append(f"각막난시가 {astig:.2f} 존재합니다. 난시교정렌즈를 고려하세요.")
        elif astig > 1.0:
            self.interpretations[eye].append(f"각막난시가 {astig:.2f} 존재합니다.")

    def analyze_bilateral_differences(self, od_data, os_data):
        al_diff = abs(od_data['AL'] - os_data['AL'])
        se_diff = abs(od_data['K (SE)'] - os_data['K (SE)'])
        
        if al_diff >= 0.3:
            self.interpretations['OD'].append(f"양안의 안축장 차이가 {al_diff:.2f}mm로 차이가 있습니다.")
            self.interpretations['OS'].append(f"양안의 안축장 차이가 {al_diff:.2f}mm로 차이가 있습니다.")
        
        if se_diff >= 0.5:
            self.interpretations['OD'].append(f"양안의 각막굴절률 차이가 {se_diff:.2f}D로 차이가 있습니다.")
            self.interpretations['OS'].append(f"양안의 각막굴절률 차이가 {se_diff:.2f}D로 차이가 있습니다.")

    def get_report(self):
        report = ""
        for eye in ['OD', 'OS']:
            report += f"\n{eye} ({'우안' if eye == 'OD' else '좌안'}):\n"
            for interp in self.interpretations[eye]:
                report += f"• {interp}\n"
        return report

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

def calculate_se(k1, k2):
    """K1과 K2의 평균값으로 SE 계산"""
    return (k1 + k2) / 2

def update_params():
    """파라미터가 변경될 때마다 SE 계산 및 상태 업데이트"""
    if 'current_params' in st.session_state:
        # OD 업데이트
        st.session_state.current_params['OD'].update({
            'AL': st.session_state.od_al,
            'ACD': st.session_state.od_acd,
            'K1': st.session_state.od_k1,
            'K2': st.session_state.od_k2,
            'K (SE)': calculate_se(st.session_state.od_k1, st.session_state.od_k2)
        })
        # OS 업데이트
        st.session_state.current_params['OS'].update({
            'AL': st.session_state.os_al,
            'ACD': st.session_state.os_acd,
            'K1': st.session_state.os_k1,
            'K2': st.session_state.os_k2,
            'K (SE)': calculate_se(st.session_state.os_k1, st.session_state.os_k2)
        })

def extract_parameters(image):
    with st.spinner('Extracting parameters from image...'):
        try:
            # 디버그 출력 추가
            st.write("Debug - Secrets available:", st.secrets)
            st.write("Debug - API_KEY value:", API_KEY)
            
            # API 키 확인
            if not API_KEY:
                st.error("API key is not set")
                return None
                
            # API 호출 전 디버깅
            st.write("Debug: Starting API call")
            
            client = OpenAI(api_key=API_KEY)
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            # API 응답 전 디버깅
            st.write("Debug: Making API request")
            
            response = client.chat.completions.create(
                model="gpt-4-vision-preview-0314",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Please analyze this ocular biometry report. The image is divided into two halves: OD (right eye) on the left and OS (left eye) on the right.

Extract ONLY these specific measurements:
1. AL: Find number after 'AL:' followed by 'mm'
2. ACD: Find number after 'ACD:' followed by 'mm'
3. K1: Find number after 'K1:' followed by 'D'
4. K2: Find number after 'K2:' followed by 'D'

IMPORTANT:
- Ignore any other measurements (TSE, TK1, TK2, etc.)
- Extract numbers only, without units
- Return values in exactly this order, separated by commas:
OD_AL, OD_ACD, OD_K1, OD_K2, OS_AL, OS_ACD, OS_K1, OS_K2"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }],
                max_tokens=300
            )
            
            # API 응답 후 디버깅
            st.write("Debug: API response received")
            st.write("Raw Response:", response)
            
            raw_response = response.choices[0].message.content.strip()
            st.write("Processed Response:", raw_response)
            
            values = [float(x.strip()) for x in raw_response.split(',')]
            if len(values) != 8:
                st.error(f"Expected 8 values, got {len(values)}")
                return None
            
            formatted_params = {
                'OD': {
                    'AL': values[0],
                    'ACD': values[1],
                    'K1': values[2],
                    'K2': values[3],
                },
                'OS': {
                    'AL': values[4],
                    'ACD': values[5],
                    'K1': values[6],
                    'K2': values[7],
                }
            }
            
            formatted_params['OD']['K (SE)'] = calculate_se(values[2], values[3])
            formatted_params['OS']['K (SE)'] = calculate_se(values[6], values[7])
            
            st.success("Parameters extracted successfully!")
            return formatted_params
            
        except Exception as e:
            st.error(f"Error in extract_parameters: {str(e)}")
            st.write("Error details:", e)
            return None

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
