# Desarrollo de una Aplicación para la Integración y Sincronización Temporal de Señales Biomédicas Multimodales

Aplicación de escritorio para la lectura, filtrado, sincronización temporal y exportación unificada a formato EDF/EDF+ de señales electromiográficas (EMG) y electrocardiográficas (ECG).

## Estructura del Proyecto

```text
TFG_Proyecto/
├── data/                      # Almacenamiento de datos de entrada (raw) y exportaciones (output)
├── src/                       # Código principal de la aplicación
│   ├── gui/                   # Interfaz gráfica de usuario y widgets interactivos
│   │   ├── main_window.py     
│   │   └── widgets.py         
│   ├── modules/               # Módulos de procesamiento
│   │   ├── ecg_module.py      
│   │   ├── emg_module.py      
│   │   ├── edf_converter.py   
│   │   └── sync_module.py     
│   ├── utils/                 # Funciones de soporte y auxiliares
│   │   └── helpers.py         
│   └── main.py                # Punto de entrada de la aplicación           
├── requirements.txt           # Listado de dependencias y librerías de Python
└── README.md                  
