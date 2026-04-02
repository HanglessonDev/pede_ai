"""Pede AI - Sistema de Pedidos com IA para Lanchonetes.

Este pacote fornece um sistema de atendimento automatizado para lanchonetes,
utilizando IA para classificar intenções, extrair itens de pedidos e
gerenciar o fluxo de atendimento via LangGraph.

Submódulos:
    config: Configuração, cardápio e prompts.
    extratores: Extração de entidades com spaCy.
    graph: Grafo de fluxo de atendimento e estado.
    roteador: Classificação de intenções com LLM.

Example:
    ```python
    from src.extratores import extrair
    from src.roteador import classificar_intencao

    classificar_intencao('quero um x-salada')
    'pedir'
    extrair('um x-salada sem tomate')
    [
        {
            'item_id': 'lanche_002',
            'quantidade': 1,
            'variante': None,
            'remocoes': ['tomate'],
        }
    ]
    ```
"""
