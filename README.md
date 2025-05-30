# senescyt-explorer

Consulta datos del sitio de Títulos de tercer de nivel de la senescyt desde consola. Usando IA Tesseract OCR para resolver el CAPTCHA. 


## Instrucciones 

Windows

~~~
git clone https://github.com/afreireo/senescyt-explorer.git
cd senescyt-explorer
python -m venv env
env\Scripts\activate
python -m pip install playwright pytesseract
python senescyt-explorer.py
~~~

Linux
~~~
git clone https://github.com/afreireo/senescyt-explorer.git
cd senescyt-explorer
python -m venv env
source env/bin/activate
python -m pip install playwright pytesseract
python senescyt-explorer.py
~~~

