import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta, timezone
import os
from app.config import settings
import logging
import numpy as np
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BlogAnalytics:
    """Класс для аналитики блога (совместим с numpy 2.x и pandas 2.2.3)"""

    def __init__(self):
        """Инициализация соединения с БД"""
        self.engine = create_engine(settings.DATABASE_URL, future=True)
        self.plots_dir = "app/static/plots"
        os.makedirs(self.plots_dir, exist_ok=True)

        # Настройка стиля для matplotlib 3.9+
        plt.style.use('default')
        sns.set_theme(style="whitegrid")

    def get_posts_daily_stats(self, days: int = 30) -> pd.DataFrame:
        """
        Получение ежедневной статистики постов

        Args:
            days: количество дней для анализа

        Returns:
            DataFrame с колонками: date, posts_count, comments_count, unique_authors
        """
        query = text("""
            SELECT 
                DATE(p.created_at) as date,
                COUNT(DISTINCT p.id) as posts_count,
                COUNT(DISTINCT c.id) as comments_count,
                COUNT(DISTINCT p.author_id) as unique_authors
            FROM posts p
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE p.created_at >= :start_date
            GROUP BY DATE(p.created_at)
            ORDER BY date
        """)

        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        df = pd.read_sql(query, self.engine, params={"start_date": start_date})

        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])

        return df

    def get_top_authors(self, limit: int = 10) -> pd.DataFrame:
        """
        Получение топ авторов по количеству постов и комментариев

        Args:
            limit: количество авторов

        Returns:
            DataFrame с колонками: author, posts_count, comments_received
        """
        query = text("""
            SELECT 
                u.username as author,
                COUNT(DISTINCT p.id) as posts_count,
                COUNT(DISTINCT c.id) as comments_received
            FROM users u
            LEFT JOIN posts p ON u.id = p.author_id
            LEFT JOIN comments c ON p.id = c.post_id
            WHERE u.is_active = true
            GROUP BY u.id, u.username
            HAVING COUNT(DISTINCT p.id) > 0
            ORDER BY posts_count DESC, comments_received DESC
            LIMIT :limit
        """)

        df = pd.read_sql(query, self.engine, params={"limit": limit})

        # Используем fillna вместо deprecated методов
        df = df.fillna(0)

        # Конвертируем в целые числа
        df['posts_count'] = df['posts_count'].astype(int)
        df['comments_received'] = df['comments_received'].astype(int)

        return df

    def get_post_versions_stats(self) -> pd.DataFrame:
        """
        Статистика по версиям постов

        Returns:
            DataFrame с колонками: change_type, count, avg_time_between_versions
        """
        query = text("""
            WITH version_changes AS (
                SELECT 
                    pv1.post_id,
                    pv1.change_type::text as change_type,
                    pv1.changed_at,
                    EXTRACT(epoch FROM (pv1.changed_at - pv2.changed_at))/3600.0 as hours_since_previous
                FROM post_versions pv1
                LEFT JOIN post_versions pv2 ON 
                    pv1.post_id = pv2.post_id 
                    AND pv2.changed_at < pv1.changed_at
                    AND pv2.changed_at = (
                        SELECT MAX(changed_at) 
                        FROM post_versions 
                        WHERE post_id = pv1.post_id AND changed_at < pv1.changed_at
                    )
            )
            SELECT 
                change_type,
                COUNT(*) as count,
                AVG(hours_since_previous) as avg_hours_between_changes
            FROM version_changes
            GROUP BY change_type
        """)

        df = pd.read_sql(query, self.engine)

        # Обработка возможных NaN значений
        df = df.fillna(0)
        df['count'] = df['count'].astype(int)

        return df

    def plot_posts_timeline(self, days: int = 30, save: bool = True) -> Optional[plt.Figure]:
        """
        Построение графика активности по дням

        Args:
            days: количество дней
            save: сохранить ли график в файл

        Returns:
            Figure объект или None
        """
        df = self.get_posts_daily_stats(days)

        if df.empty:
            logger.warning("Нет данных для построения графика")
            return None

        # Создание фигуры с подграфиками
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7))

        # График 1: Посты и комментарии
        ax1.plot(df['date'], df['posts_count'], marker='o', linewidth=2, label='Посты', color='#2ecc71')
        ax1.plot(df['date'], df['comments_count'], marker='s', linewidth=2, label='Комментарии', color='#3498db')
        ax1.set_title('Активность в блоге по дням', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Дата')
        ax1.set_ylabel('Количество')
        ax1.legend()
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)

        # График 2: Уникальные авторы
        ax2.bar(df['date'], df['unique_authors'], color='#e74c3c', alpha=0.7, width=0.8)
        ax2.set_title('Уникальные авторы по дням', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Дата')
        ax2.set_ylabel('Количество авторов')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save:
            filename = f"{self.plots_dir}/posts_timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=100, bbox_inches='tight')
            logger.info(f"График сохранен: {filename}")

        return fig

    def plot_top_authors(self, limit: int = 10, save: bool = True) -> Optional[plt.Figure]:
        """
        Построение графика топ авторов

        Args:
            limit: количество авторов
            save: сохранить ли график в файл

        Returns:
            Figure объект или None
        """
        df = self.get_top_authors(limit)

        if df.empty:
            logger.warning("Нет данных для построения графика")
            return None

        # Создание фигуры
        fig, ax = plt.subplots(figsize=(12, 6))

        # Сортировка для горизонтального графика
        df_sorted = df.sort_values('posts_count', ascending=True)
        y_pos = np.arange(len(df_sorted))

        # Создание stacked bar chart
        ax.barh(y_pos, df_sorted['posts_count'], alpha=0.7, label='Посты', color='#2ecc71')
        ax.barh(y_pos, df_sorted['comments_received'], alpha=0.5,
                label='Комментарии', left=df_sorted['posts_count'], color='#3498db')

        ax.set_title(f'Топ {limit} авторов по активности', fontsize=14, fontweight='bold')
        ax.set_xlabel('Количество')
        ax.set_ylabel('Автор')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df_sorted['author'])
        ax.legend()
        ax.grid(True, alpha=0.3, axis='x')

        # Добавление значений на график
        for i, (_, row) in enumerate(df_sorted.iterrows()):
            if row['posts_count'] > 0:
                ax.text(row['posts_count'] / 2, i, str(int(row['posts_count'])),
                        ha='center', va='center', fontweight='bold', color='white')
            if row['comments_received'] > 0:
                ax.text(row['posts_count'] + row['comments_received'] / 2, i,
                        str(int(row['comments_received'])), ha='center', va='center',
                        fontweight='bold', color='white')

        plt.tight_layout()

        if save:
            filename = f"{self.plots_dir}/top_authors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=100, bbox_inches='tight')
            logger.info(f"График сохранен: {filename}")

        return fig

    def plot_versions_distribution(self, save: bool = True) -> Optional[plt.Figure]:
        """
        Построение графика распределения типов изменений

        Args:
            save: сохранить ли график в файл

        Returns:
            Figure объект или None
        """
        df = self.get_post_versions_stats()

        if df.empty or df['count'].sum() == 0:
            logger.warning("Нет данных для построения графика")
            return None

        # Создание фигуры с подграфиками
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Круговая диаграмма
        colors = ['#2ecc71', '#3498db', '#e74c3c']

        # Фильтруем только ненулевые значения
        df_pie = df[df['count'] > 0]

        if not df_pie.empty:
            wedges, texts, autotexts = ax1.pie(
                df_pie['count'],
                labels=df_pie['change_type'],
                autopct='%1.1f%%',
                colors=colors[:len(df_pie)],
                startangle=90,
                textprops={'fontsize': 12}
            )
            ax1.set_title('Распределение типов изменений', fontsize=14, fontweight='bold')

            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
                autotext.set_fontsize(11)

        # Столбчатая диаграмма среднего времени
        df_time = df.dropna(subset=['avg_hours_between_changes'])
        df_time = df_time[df_time['avg_hours_between_changes'] > 0]

        if not df_time.empty:
            bars = ax2.bar(
                df_time['change_type'],
                df_time['avg_hours_between_changes'],
                color=colors[:len(df_time)],
                alpha=0.8
            )
            ax2.set_title('Среднее время между изменениями (часы)', fontsize=14, fontweight='bold')
            ax2.set_xlabel('Тип изменения')
            ax2.set_ylabel('Часы')
            ax2.grid(True, alpha=0.3, axis='y')

            # Добавление значений на столбцы
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width() / 2., height,
                         f'{height:.1f}', ha='center', va='bottom', fontweight='bold')

        plt.tight_layout()

        if save:
            filename = f"{self.plots_dir}/versions_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filename, dpi=100, bbox_inches='tight')
            logger.info(f"График сохранен: {filename}")

        return fig

    def generate_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Генерация полного отчета с графиками

        Args:
            days: количество дней для анализа

        Returns:
            Словарь с результатами
        """
        logger.info("Начинаем генерацию отчета...")

        try:
            # Создание всех графиков
            self.plot_posts_timeline(days)
            self.plot_top_authors()
            self.plot_versions_distribution()

            # Сохранение статистики в CSV
            report_files = {}

            df_daily = self.get_posts_daily_stats(days)
            if not df_daily.empty:
                daily_file = f"{self.plots_dir}/daily_stats.csv"
                df_daily.to_csv(daily_file, index=False)
                report_files['daily_stats'] = daily_file

            df_authors = self.get_top_authors()
            if not df_authors.empty:
                authors_file = f"{self.plots_dir}/top_authors.csv"
                df_authors.to_csv(authors_file, index=False)
                report_files['top_authors'] = authors_file

            df_versions = self.get_post_versions_stats()
            if not df_versions.empty:
                versions_file = f"{self.plots_dir}/versions_stats.csv"
                df_versions.to_csv(versions_file, index=False)
                report_files['versions_stats'] = versions_file

            logger.info(f"Отчет сохранен в {self.plots_dir}")

            return {
                "status": "success",
                "message": "Report generated successfully",
                "files": report_files,
                "plots_directory": self.plots_dir
            }

        except Exception as e:
            logger.error(f"Ошибка при генерации отчета: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


if __name__ == "__main__":
    # Пример использования
    analytics = BlogAnalytics()
    result = analytics.generate_report(days=30)
    print(result)