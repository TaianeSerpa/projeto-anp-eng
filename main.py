import logging
from src.extract import pipeline_extract       
from src.transform import pipeline_transform    
from src.load import pipeline_load              

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def main():
    logger.info(">>> INICIANDO EXECUÇÃO END-TO-END DO DATA PIPELINE <<<")

    
    pipeline_extract()

    
    pipeline_transform()

    
    pipeline_load()

    logger.info(">>> PIPELINE END-TO-END CONCLUÍDO COM SUCESSO! <<<")

if __name__ == "__main__":
    main()