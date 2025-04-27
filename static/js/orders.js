// 페이지 로드 후 실행
document.addEventListener('DOMContentLoaded', function() {
    // 날짜 범위 선택기 초기화
    initDateRangePicker();
    
    // 검색 폼 이벤트 리스너
    initSearchForm();
});

// 날짜 범위 선택기 초기화 함수
function initDateRangePicker() {
    const dateRangeInput = document.getElementById('date_range');
    
    if (dateRangeInput) {
        // flatpickr 옵션
        const options = {
            mode: "range",
            dateFormat: "Y-m-d",
            locale: {
                rangeSeparator: " ~ "
            },
            altInput: true,
            altFormat: "Y년 m월 d일",
            maxDate: new Date(),
            disableMobile: true,
            static: true
        };
        
        // flatpickr 초기화
        const datePicker = flatpickr(dateRangeInput, options);
        
        // 빠른 날짜 선택 버튼 추가
        const quickDateButtons = document.createElement('div');
        quickDateButtons.className = 'quick-date-buttons mt-2';
        quickDateButtons.innerHTML = `
            <button type="button" class="btn btn-sm btn-outline-secondary me-2" data-range="오늘">오늘</button>
            <button type="button" class="btn btn-sm btn-outline-secondary me-2" data-range="최근 일주일">최근 일주일</button>
            <button type="button" class="btn btn-sm btn-outline-secondary" data-range="최근 한달">최근 한달</button>
        `;
        
        // 날짜 입력 필드 다음에 버튼 추가
        dateRangeInput.parentNode.appendChild(quickDateButtons);
        
        // 빠른 날짜 선택 버튼 이벤트 리스너
        const buttons = quickDateButtons.querySelectorAll('button');
        buttons.forEach(button => {
            button.addEventListener('click', function() {
                const range = this.getAttribute('data-range');
                dateRangeInput.value = range;
                // 검색 폼 제출
                document.getElementById('searchForm').submit();
            });
        });
    }
}

// 검색 폼 초기화 함수
function initSearchForm() {
    const searchForm = document.getElementById('searchForm');
    
    if (searchForm) {
        // 검색어 입력 시 엔터 키 처리
        const searchInput = document.getElementById('search');
        if (searchInput) {
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    searchForm.submit();
                }
            });
        }
        
        // 상태 선택 변경 시 자동 제출
        const statusSelect = document.getElementById('status');
        if (statusSelect) {
            statusSelect.addEventListener('change', function() {
                searchForm.submit();
            });
        }
    }
} 