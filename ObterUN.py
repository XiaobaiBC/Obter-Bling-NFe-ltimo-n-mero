import requests
import json
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
from auth import BlingAuth

class NFeTipo(Enum):
    """NFe类型枚举"""
    ENTRADA = 0  # 入库
    SAIDA = 1    # 出库

@dataclass
class Config:
    """配置类，存储所有配置参数"""
    API_BASE_URL: str = "https://api.bling.com.br/Api/v3"
    MAX_WORKERS: int = 2
    NFE_DIGITS: int = 6

class BlingNFeClient:
    """处理Bling NFe API的客户端类"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }

    def get_nfe_info(self, tipo: NFeTipo) -> Optional[str]:
        """
        获取指定类型的NFe信息
        
        Args:
            tipo: NFe类型 (ENTRADA 或 SAIDA)
            
        Returns:
            Optional[str]: NFe编号，如果未找到则返回None
        """
        url = f"{Config.API_BASE_URL}/nfe"
        params = {
            "pagina": 1,
            "limite": 1,
            "tipo": tipo.value
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get('data') and response_data['data']:
                numero = response_data['data'][0].get('numero')
                tipo_desc = "入库" if tipo == NFeTipo.ENTRADA else "出库"
                print(f"NFe编号 ({tipo_desc}): {numero}")
                return numero
            
            tipo_desc = "入库" if tipo == NFeTipo.ENTRADA else "出库"
            print(f"未找到NFe编号 ({tipo_desc})")
            return None

        except requests.exceptions.RequestException as e:
            print(f"请求NFe信息时发生错误 (tipo={tipo.name}): {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"解析NFe响应时发生错误 (tipo={tipo.name}): {str(e)}")
            return None

    def get_multiple_nfe_info(self) -> Tuple[Optional[str], Optional[str]]:
        """
        并行获取入库和出库两种类型的NFe信息
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (入库NFe编号, 出库NFe编号)
        """
        with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as executor:
            future_entrada = executor.submit(self.get_nfe_info, NFeTipo.ENTRADA)
            future_saida = executor.submit(self.get_nfe_info, NFeTipo.SAIDA)
            return future_entrada.result(), future_saida.result()

class NFEProcessor:
    """NFe处理器类，处理NFe相关的业务逻辑"""
    
    @staticmethod
    def compare_nfe_numbers(numero_entrada: Optional[str], numero_saida: Optional[str]) -> Optional[str]:
        """
        比较入库和出库NFe编号并返回最大值
        
        Args:
            numero_entrada: 入库NFe编号
            numero_saida: 出库NFe编号
            
        Returns:
            Optional[str]: 格式化后的最大NFe编号
        """
        if not (numero_entrada and numero_saida):
            return None

        try:
            entrada_int = int(numero_entrada)
            saida_int = int(numero_saida)
            max_numero = max(entrada_int, saida_int)
            return f"{max_numero:0{Config.NFE_DIGITS}d}"
        except ValueError as e:
            print(f"比较NFe编号时发生错误: {str(e)}")
            return None

def main():
    """主函数"""
    auth = BlingAuth()
    
    try:
        print("正在获取授权码...")
        auth_code = auth.get_authorization_code()
        if not auth_code:
            raise ValueError("无法获取授权码")

        print("正在获取访问令牌...")
        token_info = auth.get_access_token(auth_code)
        access_token = token_info.get('access_token')
        if not access_token:
            raise ValueError("无法获取访问令牌")

        # 创建NFe客户端并获取信息
        client = BlingNFeClient(access_token)
        numero_entrada, numero_saida = client.get_multiple_nfe_info()

        # 处理结果
        max_numero = NFEProcessor.compare_nfe_numbers(numero_entrada, numero_saida)
        if max_numero:
            print(f"\n最大的NFe编号是: {max_numero}")
        else:
            print("\n无法确定最大的NFe编号")

    except Exception as e:
        print(f"程序执行出错: {str(e)}")

if __name__ == "__main__":
    main()
